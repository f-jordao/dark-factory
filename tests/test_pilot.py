import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from dark_factory.controller import Controller
from dark_factory.models import Policy
from dark_factory.pilot import FixtureGitHub
from dark_factory.state import State


PROJECT = Path(__file__).resolve().parent.parent


class PilotTests(unittest.TestCase):
    def test_fixture_cannot_impersonate_real_repository_or_publish(self):
        github = FixtureGitHub(PROJECT / "examples/reviews/known-bug.json")
        with self.assertRaisesRegex(RuntimeError, "cannot publish"):
            github.publish(github.current, "key", {})
        with self.assertRaisesRegex(RuntimeError, "cannot access"):
            github.find_published_review(github.current, "key")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            data = dict(github.data, repo="f-jordao/dark-factory")
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "reserved"):
                FixtureGitHub(path)

    def test_fixture_uses_same_claims_and_does_not_review_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            state = State(Path(directory) / "state.sqlite3")
            self.addCleanup(state.close)
            github = FixtureGitHub(PROJECT / "examples/reviews/known-bug.json")
            worker = Mock()
            worker.review.return_value = {
                "schema_version": 1, "head_sha": github.current.head,
                "base_sha": github.current.base, "summary": "Fixture result",
                "spec_status": "available", "findings": [],
            }
            controller = Controller(github, state, Policy(("tests",)), worker)
            self.assertEqual(controller.reconcile(1)["action"], "would_review")
            self.assertEqual(worker.review.call_count, 0)
            self.assertEqual(controller.reconcile(1, execute=True)["action"], "reviewed")
            self.assertEqual(controller.reconcile(1, execute=True)["review_invocations"], 0)
            self.assertEqual(worker.review.call_count, 1)


if __name__ == "__main__":
    unittest.main()
