import json

from .models import Snapshot


class FixtureGitHub:
    """An explicit local fixture source; never attests CI for a real GitHub PR."""

    def __init__(self, path):
        self.data = json.loads(path.read_text())
        if self.data["repo"] != "offline/pilot":
            raise ValueError("Pilot packets must use the reserved offline/pilot namespace")
        self.current = Snapshot(
            repo=self.data["repo"], number=self.data["pr_number"], state="open",
            draft=False, head=self.data["head_sha"], base=self.data["base_sha"],
            title=self.data["title"], body=self.data["description"],
            checks={"tests": "success"}, changed_files=len(self.data["files"]),
        )

    def snapshot(self, number):
        return self.current

    def packet(self, snapshot, max_bytes):
        if len(json.dumps(self.data).encode()) > max_bytes:
            raise ValueError("Fixture exceeds the packet size limit")
        return self.data

    def find_published_review(self, snapshot, key):
        raise RuntimeError("Pilot fixtures cannot access GitHub")

    def publish(self, snapshot, key, result):
        raise RuntimeError("Pilot fixtures cannot publish to GitHub")
