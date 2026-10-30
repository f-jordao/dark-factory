from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from .controller import Controller
from .models import Policy, Snapshot
from .state import State


class DemoGitHub:
    """Offline GitHub substitute. It never connects to GitHub."""

    def __init__(self, snapshot):
        self.current = snapshot
        self.reviews = {}
        self.publication_error = False

    def snapshot(self, number):
        return self.current

    def packet(self, snapshot, max_bytes):
        return {
            "schema_version": 1, "repo": snapshot.repo, "pr_number": snapshot.number,
            "head_sha": snapshot.head, "base_sha": snapshot.base,
            "title": "Example change", "description": "Return the expected value.",
            "files": [{"path": "example.py", "patch": "@@ -1 +1 @@\n-return 1\n+return 2"}],
            "standards": [],
        }

    def find_published_review(self, snapshot, key):
        return self.reviews.get(key)

    def publish(self, snapshot, key, result):
        if self.publication_error:
            raise RuntimeError("Simulated GitHub publication failure")
        self.reviews[key] = len(self.reviews) + 1
        return self.reviews[key]


class DemoReviewer:
    """A deterministic fixture, never an LLM. Only used by demo and tests."""

    def __init__(self):
        self.calls = 0
        self.on_review = None

    def review(self, key, packet):
        self.calls += 1
        if self.on_review:
            self.on_review()
        return {
            "schema_version": 1, "head_sha": packet["head_sha"],
            "base_sha": packet["base_sha"],
            "summary": "Offline fixture: the implementation differs from the requirement.",
            "spec_status": "available",
            "findings": [{
                "path": "example.py", "line": 1, "axis": "spec", "severity": "medium",
                "body": "Fixture finding: the requirement expects the previous return value.",
            }],
        }


def run_demo():
    base = Snapshot(
        "example/repository", 42, "open", True, "a" * 40, "b" * 40,
        checks={"tests": "pending"}, changed_files=1,
    )
    github, reviewer = DemoGitHub(base), DemoReviewer()
    policy = Policy(("tests",))
    stages = [
        ("Draft PR", base),
        ("Ready, CI pending", replace(base, draft=False)),
        ("CI green", replace(base, draft=False, checks={"tests": "success"})),
        ("Duplicate trigger", replace(base, draft=False, checks={"tests": "success"})),
        ("New commit, CI pending", replace(base, draft=False, head="c" * 40)),
        ("New commit, CI green", replace(base, draft=False, head="c" * 40, checks={"tests": "success"})),
        ("Merged", replace(base, draft=False, head="c" * 40, state="closed")),
    ]
    with TemporaryDirectory(prefix="dark-factory-demo-") as directory:
        state = State(Path(directory) / "state.sqlite3")
        controller = Controller(github, state, policy, reviewer)
        events = []
        for label, snapshot in stages:
            github.current = snapshot
            event = controller.reconcile(42, execute=True, publish=True)
            events.append({
                "step": label, "action": event["action"],
                "reason": event.get("reason"),
                "review_worker_runs": event["review_invocations"],
            })
        state.close()
    return {
        "mode": "offline_demo", "llm_calls": 0, "github_requests": 0,
        "fixture_review_runs": reviewer.calls, "events": events,
    }
