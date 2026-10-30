import base64
import json
import re
import subprocess

from .models import Snapshot


class GitHub:
    """Use the user's existing gh authentication; no tokens in project config."""

    def __init__(self, repo):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("Repository must be owner/name")
        self.repo = repo
        self.root = "repos/" + repo

    def api(self, path, payload=None, paginate=False, optional=False):
        args = ["gh", "api", path]
        if paginate:
            args += ["--paginate", "--slurp"]
        if payload is not None:
            args += ["--method", "POST", "--input", "-"]
        completed = subprocess.run(
            args, input=json.dumps(payload) if payload is not None else None,
            capture_output=True, text=True, timeout=60,
        )
        if completed.returncode:
            if optional and "(HTTP 404)" in completed.stderr:
                return None
            raise RuntimeError(completed.stderr.strip() or "GitHub request failed")
        return json.loads(completed.stdout)

    def open_prs(self):
        pages = self.api(self.root + "/pulls?state=open&per_page=100", paginate=True)
        return [pr["number"] for page in pages for pr in page]

    def snapshot(self, number):
        if type(number) is not int or number <= 0:
            raise ValueError("PR number must be a positive integer")
        pr = self.api(self.root + "/pulls/" + str(number))
        checks = {}
        if pr["state"] == "open" and not pr["draft"]:
            head = pr["head"]["sha"]
            pages = self.api(
                self.root + "/commits/" + head + "/check-runs?per_page=100&filter=latest",
                paginate=True,
            )
            candidates = {}
            for page in pages:
                for check in page["check_runs"]:
                    name = check["name"]
                    candidates.setdefault(name, []).append(check)
            for name, runs in candidates.items():
                apps = {run.get("app", {}).get("id") for run in runs}
                if len(apps) > 1:
                    checks[name] = "ambiguous"
                    continue
                latest = max(runs, key=lambda run: run["id"])
                checks[name] = (
                    latest.get("conclusion") or "pending"
                    if latest["status"] == "completed" else "pending"
                )
            pages = self.api(
                self.root + "/commits/" + head + "/statuses?per_page=100", paginate=True
            )
            statuses = {}
            for page in pages:
                for status in page:
                    name = status["context"]
                    if name not in statuses or status["id"] > statuses[name]["id"]:
                        statuses[name] = status
            for name, status in statuses.items():
                checks[name] = "ambiguous" if name in checks else status["state"]
        return Snapshot(
            repo=self.repo, number=number, state=pr["state"], draft=pr["draft"],
            head=pr["head"]["sha"], base=pr["base"]["sha"], title=pr["title"],
            body=pr.get("body") or "", checks=checks, changed_files=pr["changed_files"],
        )

    def packet(self, snapshot, max_bytes):
        pages = self.api(
            self.root + "/pulls/" + str(snapshot.number) + "/files?per_page=100",
            paginate=True,
        )
        files = [file for page in pages for file in page]
        if len(files) != snapshot.changed_files:
            raise ValueError("GitHub returned an incomplete changed-file list")
        text_files = []
        for file in files:
            patch = file.get("patch")
            if not isinstance(patch, str) or (
                file.get("changes", 0) > 0 and not patch.startswith("@@")
            ):
                raise ValueError(
                    "Missing, binary or truncated patch requires a human review: "
                    + file["filename"]
                )
            plus = sum(line.startswith("+") for line in patch.splitlines())
            minus = sum(line.startswith("-") for line in patch.splitlines())
            if (plus, minus) != (file["additions"], file["deletions"]):
                raise ValueError("Incomplete patch requires a human review: " + file["filename"])
            text_files.append({"path": file["filename"], "patch": patch})
        standards = []
        for path in ("AGENTS.md", "CONTRIBUTING.md", "CODING_STANDARDS.md"):
            data = self.api(
                self.root + "/contents/" + path + "?ref=" + snapshot.base, optional=True
            )
            if isinstance(data, dict) and data.get("encoding") == "base64":
                content = base64.b64decode(data["content"]).decode("utf-8")
                standards.append({"path": path, "content": content})
        packet = {
            "schema_version": 1, "repo": snapshot.repo, "pr_number": snapshot.number,
            "head_sha": snapshot.head, "base_sha": snapshot.base,
            "title": snapshot.title, "description": snapshot.body,
            "files": text_files, "standards": standards,
        }
        if len(json.dumps(packet).encode()) > max_bytes:
            raise ValueError("Review packet exceeds the configured size limit")
        return packet

    def find_published_review(self, snapshot, key):
        login = self.api("user")["login"]
        marker = "<!-- dark-factory:review:" + key + " -->"
        pages = self.api(
            self.root + "/pulls/" + str(snapshot.number) + "/reviews?per_page=100",
            paginate=True,
        )
        for page in pages:
            for review in page:
                if (
                    review["user"]["login"] == login
                    and review["commit_id"] == snapshot.head
                    and marker in (review.get("body") or "")
                    and review["state"] != "PENDING"
                ):
                    return review["id"]
        return None

    def publish(self, snapshot, key, result):
        marker = "<!-- dark-factory:review:" + key + " -->"
        comments = [
            {
                "path": finding["path"], "line": finding["line"], "side": "RIGHT",
                "body": "**" + finding["severity"].upper() + " · "
                + finding["axis"].capitalize() + "**\n\n" + finding["body"],
            }
            for finding in result["findings"]
        ]
        payload = {
            "event": "COMMENT", "commit_id": snapshot.head,
            "body": result["summary"] + "\n\n"
            + "Spec: " + result["spec_status"] + ".\n\n" + marker,
        }
        if comments:
            payload["comments"] = comments
        return self.api(
            self.root + "/pulls/" + str(snapshot.number) + "/reviews", payload=payload
        )["id"]
