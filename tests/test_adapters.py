import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from dark_factory.cli import load_policy
from dark_factory.github import GitHub
from dark_factory.models import Policy, Snapshot
from dark_factory.reviewer import CommandReviewer


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.github = GitHub("example/repo")
        self.pr = {
            "state": "open", "draft": False, "head": {"sha": "a" * 40},
            "base": {"sha": "b" * 40}, "title": "PR", "body": None, "changed_files": 1,
        }
        self.snapshot = Snapshot("example/repo", 1, "open", False, "a" * 40, "b" * 40)

    def check(self, id, name="tests", app=1, status="completed", conclusion="success"):
        return {
            "id": id, "name": name, "app": {"id": app},
            "status": status, "conclusion": conclusion,
        }

    def test_latest_check_attempt_wins_over_previous_success(self):
        self.github.api = Mock(side_effect=[
            self.pr,
            [{"check_runs": [self.check(1), self.check(2, status="in_progress")]}],
            [[]],
        ])
        self.assertEqual(self.github.snapshot(1).checks["tests"], "pending")

    def test_same_check_name_from_multiple_apps_is_ambiguous(self):
        self.github.api = Mock(side_effect=[
            self.pr, [{"check_runs": [self.check(1), self.check(2, app=2)]}], [[]],
        ])
        self.assertEqual(self.github.snapshot(1).checks["tests"], "ambiguous")

    def test_status_and_check_name_collision_does_not_pass(self):
        self.github.api = Mock(side_effect=[
            self.pr, [{"check_runs": [self.check(1)]}],
            [[{"id": 1, "context": "tests", "state": "success"}]],
        ])
        self.assertEqual(self.github.snapshot(1).checks["tests"], "ambiguous")

    def test_incomplete_or_binary_patch_is_not_sent_to_worker(self):
        snapshot = Snapshot(
            "example/repo", 1, "open", False, "a" * 40, "b" * 40, changed_files=1
        )
        for file in (
            {"filename": "image.png", "changes": 0, "additions": 0, "deletions": 0},
            {"filename": "file.py", "patch": "@@ -1 +1 @@\n-old\n+new",
             "changes": 100, "additions": 50, "deletions": 50},
        ):
            self.github.api = Mock(return_value=[[file]])
            with self.assertRaises(ValueError):
                self.github.packet(snapshot, 500_000)

    def test_review_post_is_comment_with_exact_commit_and_marker(self):
        self.github.api = Mock(return_value={"id": 7})
        result = {"summary": "No findings", "spec_status": "missing", "findings": []}
        self.assertEqual(self.github.publish(self.snapshot, "key", result), 7)
        payload = self.github.api.call_args.kwargs["payload"]
        self.assertEqual(payload["event"], "COMMENT")
        self.assertEqual(payload["commit_id"], "a" * 40)
        self.assertIn("dark-factory:review:key", payload["body"])

    def test_dedup_marker_must_belong_to_authenticated_reviewer(self):
        review = {
            "id": 99, "commit_id": "a" * 40, "state": "COMMENTED",
            "user": {"login": "someone-else"}, "body": "<!-- dark-factory:review:key -->",
        }
        self.github.api = Mock(side_effect=[{"login": "owner"}, [[review]]])
        self.assertIsNone(self.github.find_published_review(self.snapshot, "key"))

    def test_command_worker_receives_paths_as_arguments_without_shell(self):
        with tempfile.TemporaryDirectory(prefix="factory path with spaces ") as directory:
            root = Path(directory)
            worker = root / "worker.py"
            worker.write_text(
                "import json,sys\n"
                "packet=json.load(open(sys.argv[1]))\n"
                "json.dump({'received':packet},open(sys.argv[2],'w'))\n"
            )
            policy = Policy(("tests",), (sys.executable, str(worker), "{input}", "{output}"))
            reviewer = CommandReviewer(policy, root / "runs", root)
            packet = {"title": "$(touch NEVER_EXECUTE_THIS)"}
            self.assertEqual(reviewer.review("key", packet)["received"], packet)
            self.assertFalse((root / "NEVER_EXECUTE_THIS").exists())

    def test_worker_timeout_allows_graceful_cancellation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worker = root / "worker.py"
            worker.write_text(
                "import pathlib,signal,sys,time\n"
                "def stop(signum,frame):\n"
                "    pathlib.Path('cancelled').write_text('confirmed')\n"
                "    sys.exit(0)\n"
                "signal.signal(signal.SIGTERM,stop)\n"
                "time.sleep(60)\n"
            )
            policy = Policy(("tests",), (sys.executable, str(worker)), timeout_seconds=1)
            reviewer = CommandReviewer(policy, root / "runs", root)
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                reviewer.review("key", {})
            self.assertEqual((root / "cancelled").read_text(), "confirmed")

    def test_changed_worker_artifact_invalidates_policy_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "prompt.md").write_text("review instructions")
            (root / "profile.json").write_text('{"tools":[]}')
            config = root / "config.json"
            config.write_text(json.dumps({
                "review_prompt": "prompt.md", "review_artifacts": ["profile.json"],
            }))
            before, _ = load_policy(config)
            (root / "profile.json").write_text('{"tools":["shell"]}')
            after, _ = load_policy(config)
            self.assertNotEqual(before.digest, after.digest)
            config.write_text(json.dumps({
                "review_prompt": "prompt.md", "review_artifacts": "profile.json",
            }))
            with self.assertRaisesRegex(ValueError, "review_artifacts"):
                load_policy(config)


if __name__ == "__main__":
    unittest.main()
