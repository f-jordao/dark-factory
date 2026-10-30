import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from dark_factory.controller import Controller
from dark_factory.demo import DemoGitHub, DemoReviewer, run_demo
from dark_factory.models import Policy, Snapshot, review_key, validate_result
from dark_factory.state import State


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.state = State(Path(self.directory.name) / "state.sqlite3")
        self.snapshot = Snapshot(
            "example/repo", 1, "open", False, "a" * 40, "b" * 40,
            checks={"tests": "success"}, changed_files=1,
        )
        self.github = DemoGitHub(self.snapshot)
        self.reviewer = DemoReviewer()
        self.policy = Policy(("tests",))
        self.controller = Controller(self.github, self.state, self.policy, self.reviewer)

    def tearDown(self):
        self.state.close()
        self.directory.cleanup()

    def run_review(self, **options):
        return self.controller.reconcile(1, execute=True, publish=True, **options)

    def test_draft_pending_failed_missing_and_closed_never_invoke_worker(self):
        cases = [
            replace(self.snapshot, draft=True),
            replace(self.snapshot, checks={"tests": "pending"}),
            replace(self.snapshot, checks={"tests": "failure"}),
            replace(self.snapshot, checks={"tests": "skipped"}),
            replace(self.snapshot, checks={"tests": "neutral"}),
            replace(self.snapshot, checks={}),
            replace(self.snapshot, state="closed"),
        ]
        for snapshot in cases:
            with self.subTest(snapshot=snapshot):
                self.github.current = snapshot
                result = self.run_review()
                self.assertEqual(result["review_invocations"], 0)
        self.assertEqual(self.reviewer.calls, 0)
        self.assertEqual(self.github.reviews, {})

    def test_empty_required_checks_do_not_treat_no_ci_as_green(self):
        self.controller.policy = Policy(())
        result = self.run_review()
        self.assertEqual(result["reason"], "checks_not_configured")
        self.assertEqual(self.reviewer.calls, 0)

    def test_inspection_neither_reviews_nor_publishes(self):
        result = self.controller.reconcile(1)
        self.assertEqual(result["action"], "would_review")
        self.assertEqual(self.reviewer.calls, 0)
        self.assertEqual(self.state.list(), [])

    def test_duplicate_trigger_reviews_and_publishes_once(self):
        self.assertEqual(self.run_review()["action"], "published")
        result = self.run_review()
        self.assertEqual(result["action"], "published")
        self.assertEqual(result["review_invocations"], 0)
        self.assertEqual(self.reviewer.calls, 1)
        self.assertEqual(len(self.github.reviews), 1)

    def test_new_commit_waits_for_its_own_green_checks(self):
        self.run_review()
        self.github.current = replace(self.snapshot, head="c" * 40, checks={"tests": "pending"})
        self.assertEqual(self.run_review()["action"], "waiting")
        self.assertEqual(self.reviewer.calls, 1)
        self.github.current = replace(self.github.current, checks={"tests": "success"})
        self.assertEqual(self.run_review()["action"], "published")
        self.assertEqual(self.reviewer.calls, 2)

    def test_new_base_invalidates_previous_review(self):
        self.run_review()
        self.github.current = replace(self.snapshot, base="c" * 40)
        self.assertEqual(self.run_review()["action"], "published")
        self.assertEqual(self.reviewer.calls, 2)

    def test_new_policy_invalidates_previous_review(self):
        self.run_review()
        self.controller.policy = replace(self.policy, prompt_digest="changed")
        self.run_review()
        self.assertEqual(self.reviewer.calls, 2)

    def test_commit_arriving_during_review_discards_publication(self):
        self.reviewer.on_review = lambda: setattr(
            self.github, "current", replace(self.snapshot, head="c" * 40)
        )
        result = self.run_review()
        self.assertEqual(result["action"], "stale")
        self.assertEqual(self.reviewer.calls, 1)
        self.assertEqual(self.github.reviews, {})

    def test_ci_regression_during_review_defers_publication(self):
        self.reviewer.on_review = lambda: setattr(
            self.github, "current", replace(self.snapshot, checks={"tests": "pending"})
        )
        self.assertEqual(self.run_review()["action"], "waiting")
        self.assertEqual(self.github.reviews, {})
        self.github.current = self.snapshot
        self.assertEqual(self.run_review()["action"], "published")
        self.assertEqual(self.reviewer.calls, 1)

    def test_change_while_collecting_packet_does_not_invoke_worker(self):
        original = self.github.packet

        def changing_packet(snapshot, limit):
            packet = original(snapshot, limit)
            self.github.current = replace(snapshot, head="c" * 40)
            return packet

        self.github.packet = changing_packet
        self.assertEqual(self.run_review()["reason"], "changed_before_review")
        self.assertEqual(self.reviewer.calls, 0)

    def test_publication_retry_reuses_saved_findings(self):
        self.github.publication_error = True
        with self.assertRaisesRegex(RuntimeError, "publication failure"):
            self.run_review()
        key = review_key(self.snapshot, self.policy)
        self.assertEqual(self.state.get(key)["status"], "reviewed")
        self.github.publication_error = False
        self.assertEqual(self.run_review()["action"], "published")
        self.assertEqual(self.reviewer.calls, 1)

    def test_ambiguous_successful_post_is_reconciled_without_duplicate(self):
        original = self.github.publish

        def ambiguous_post(snapshot, key, result):
            original(snapshot, key, result)
            raise RuntimeError("Connection lost after GitHub accepted the review")

        self.github.publish = ambiguous_post
        with self.assertRaises(RuntimeError):
            self.run_review()
        self.github.publish = original
        self.assertEqual(self.run_review()["action"], "published")
        self.assertEqual(self.reviewer.calls, 1)
        self.assertEqual(len(self.github.reviews), 1)

    def test_execute_and_publish_are_independent(self):
        self.assertEqual(
            self.controller.reconcile(1, execute=True)["action"], "reviewed"
        )
        self.assertEqual(self.github.reviews, {})
        self.assertEqual(self.controller.reconcile(1, publish=True)["action"], "published")
        self.assertEqual(self.reviewer.calls, 1)

    def test_failed_review_requires_explicit_retry(self):
        with patch.object(self.reviewer, "review", side_effect=ValueError("bad output")):
            with self.assertRaises(ValueError):
                self.run_review()
        self.assertEqual(self.run_review()["action"], "failed")
        self.assertEqual(self.reviewer.calls, 0)
        self.assertEqual(self.run_review(retry=True)["action"], "published")
        self.assertEqual(self.reviewer.calls, 1)

    def test_partial_packet_does_not_invoke_worker(self):
        with patch.object(self.github, "packet", side_effect=ValueError("incomplete patch")):
            with self.assertRaises(ValueError):
                self.run_review()
        self.assertEqual(self.reviewer.calls, 0)

    def test_failed_inspection_can_retry_without_repeating_agent_work(self):
        with patch.object(self.github, "packet", side_effect=RuntimeError("temporary read error")):
            with self.assertRaises(RuntimeError):
                self.run_review()
        self.assertEqual(self.reviewer.calls, 0)
        self.assertEqual(self.run_review()["action"], "published")
        self.assertEqual(self.reviewer.calls, 1)

    def test_parallel_review_claims_are_exclusive_even_with_retry(self):
        other = State(Path(self.directory.name) / "state.sqlite3")
        self.addCleanup(other.close)
        key = review_key(self.snapshot, self.policy)
        owner = self.state.claim_review(key, self.snapshot, self.policy)
        self.assertIsNotNone(owner)
        self.assertIsNone(other.claim_review(key, self.snapshot, self.policy))
        self.assertIsNone(other.claim_review(key, self.snapshot, self.policy, retry=True))

    def test_parallel_publication_claims_are_exclusive(self):
        self.controller.reconcile(1, execute=True)
        other = State(Path(self.directory.name) / "state.sqlite3")
        self.addCleanup(other.close)
        key = review_key(self.snapshot, self.policy)
        self.assertIsNotNone(self.state.claim_publication(key))
        self.assertIsNone(other.claim_publication(key))

    def test_expired_review_is_not_automatically_repeated(self):
        key = review_key(self.snapshot, self.policy)
        self.state.claim_review(key, self.snapshot, self.policy)
        self.state.db.execute("UPDATE reviews SET lease_until=0 WHERE key=?", (key,))
        self.assertEqual(self.run_review()["action"], "running")
        self.assertEqual(self.reviewer.calls, 0)
        self.assertEqual(self.run_review(retry=True)["action"], "published")

    def test_result_rejects_wrong_revision_or_unanchored_findings(self):
        packet = self.github.packet(self.snapshot, 500_000)
        result = self.reviewer.review("fixture", packet)
        for invalid in (
            dict(result, head_sha="c" * 40),
            dict(result, findings=[dict(result["findings"][0], line=100)]),
            dict(result, findings=[dict(result["findings"][0], path="outside.py")]),
            dict(result, findings=[dict(result["findings"][0], line=True)]),
            dict(result, findings=result["findings"] * 2),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_result(invalid, packet)

    def test_review_state_survives_process_restart(self):
        self.controller.reconcile(1, execute=True)
        self.state.close()
        self.state = State(Path(self.directory.name) / "state.sqlite3")
        self.controller.state = self.state
        self.assertEqual(self.run_review()["action"], "published")
        self.assertEqual(self.reviewer.calls, 1)

    def test_closed_pr_is_recorded_and_removed_from_active_monitoring(self):
        self.run_review()
        self.assertEqual(self.state.active_prs(self.snapshot.repo), [1])
        self.github.current = replace(self.snapshot, state="closed")
        self.assertEqual(self.run_review()["action"], "stopped")
        self.assertEqual(self.state.active_prs(self.snapshot.repo), [])
        self.assertEqual(self.state.observations()[0]["state"], "closed")
        self.assertEqual(self.reviewer.calls, 1)

    def test_offline_demo_has_no_external_calls_and_two_fixture_reviews(self):
        result = run_demo()
        self.assertEqual(result["llm_calls"], 0)
        self.assertEqual(result["github_requests"], 0)
        self.assertEqual(result["fixture_review_runs"], 2)
        self.assertEqual(result["events"][-1]["action"], "stopped")


if __name__ == "__main__":
    unittest.main()
