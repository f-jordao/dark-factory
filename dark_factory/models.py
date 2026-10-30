import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class Snapshot:
    repo: str
    number: int
    state: str
    draft: bool
    head: str
    base: str
    title: str = ""
    body: str = ""
    checks: Dict[str, str] = field(default_factory=dict)
    changed_files: int = 0


@dataclass(frozen=True)
class Policy:
    required_checks: Tuple[str, ...]
    review_command: Tuple[str, ...] = ()
    review_version: str = "v1"
    prompt_digest: str = ""
    timeout_seconds: int = 900
    max_patch_bytes: int = 500_000

    @property
    def digest(self):
        payload = {
            "required_checks": self.required_checks,
            "review_command": self.review_command,
            "review_version": self.review_version,
            "prompt_digest": self.prompt_digest,
            "max_patch_bytes": self.max_patch_bytes,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def review_key(snapshot, policy):
    parts = [snapshot.repo, snapshot.number, snapshot.head, snapshot.base, policy.digest]
    return hashlib.sha256(json.dumps(parts).encode()).hexdigest()


def eligibility(snapshot, policy):
    """Return a machine-readable reason. Only 'eligible' permits reasoning."""
    if snapshot.state != "open":
        return "closed"
    if snapshot.draft:
        return "draft"
    if not policy.required_checks:
        return "checks_not_configured"
    if not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in (snapshot.head, snapshot.base)):
        return "invalid_revision"
    for name in policy.required_checks:
        state = snapshot.checks.get(name)
        if state is None:
            return "check_missing:" + name
        if state != "success":
            return "check_not_green:" + name
    return "eligible"


def same_revision(left, right):
    return (left.repo, left.number, left.head, left.base) == (
        right.repo, right.number, right.head, right.base
    )


def added_side_lines(patch):
    """New-side lines in a GitHub file patch, including reviewable context."""
    lines = set()
    current = None
    for text in patch.splitlines():
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", text)
        if hunk:
            current = int(hunk.group(1))
        elif current is not None and text.startswith(("+", " ")):
            lines.add(current)
            current += 1
    return lines


def validate_result(result, packet):
    if (
        not isinstance(result, dict)
        or type(result.get("schema_version")) is not int
        or result["schema_version"] != 1
    ):
        raise ValueError("Review output must be a schema_version=1 JSON object")
    if (result.get("head_sha"), result.get("base_sha")) != (
        packet["head_sha"], packet["base_sha"]
    ):
        raise ValueError("Review output does not match the requested revision")
    summary = result.get("summary")
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 10_000:
        raise ValueError("Review summary must be nonempty and at most 10000 characters")
    if result.get("spec_status") not in ("available", "missing"):
        raise ValueError("spec_status must be available or missing")
    findings = result.get("findings")
    if not isinstance(findings, list) or len(findings) > 30:
        raise ValueError("findings must be a list with at most 30 items")
    anchors = {
        file["path"]: added_side_lines(file["patch"]) for file in packet["files"]
    }
    seen = set()
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("Each finding must be an object")
        path, line = finding.get("path"), finding.get("line")
        if not isinstance(path, str) or type(line) is not int:
            raise ValueError("Findings require a string path and integer line")
        if line not in anchors.get(path, set()):
            raise ValueError("Finding is outside the reviewable new-side diff")
        if finding.get("severity") not in ("high", "medium", "low"):
            raise ValueError("Invalid finding severity")
        if finding.get("axis") not in ("standards", "spec"):
            raise ValueError("Invalid finding axis")
        if result["spec_status"] == "missing" and finding["axis"] == "spec":
            raise ValueError("Spec findings require an available specification")
        body = finding.get("body")
        if not isinstance(body, str) or not body.strip() or len(body) > 3000:
            raise ValueError("Finding body must be nonempty and at most 3000 characters")
        identity = (path, line, body)
        if identity in seen:
            raise ValueError("Duplicate finding")
        seen.add(identity)
    return result
