import argparse
import hashlib
import json
import sys
from pathlib import Path

from .controller import Controller
from .demo import run_demo
from .github import GitHub
from .models import Policy
from .reviewer import CommandReviewer
from .state import State


def load_policy(path):
    path = Path(path).resolve()
    config = json.loads(path.read_text())
    checks, command = config.get("required_checks", []), config.get("review_command", [])
    if not isinstance(checks, list) or not all(isinstance(v, str) and v for v in checks):
        raise ValueError("required_checks must be a list of nonempty check names")
    if len(set(checks)) != len(checks):
        raise ValueError("required_checks contains duplicates")
    if not isinstance(command, list) or not all(isinstance(v, str) and v for v in command):
        raise ValueError("review_command must be an argument list, never a shell string")
    version = config.get("review_version", "v1")
    if not isinstance(version, str) or not version:
        raise ValueError("review_version must be a nonempty string")
    timeout, limit = config.get("timeout_seconds", 900), config.get("max_patch_bytes", 500_000)
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise ValueError("timeout_seconds must be between 1 and 3600")
    if type(limit) is not int or not 1 <= limit <= 5_000_000:
        raise ValueError("max_patch_bytes must be between 1 and 5000000")
    prompt = config.get("review_prompt", "prompts/pr-review.md")
    artifacts = config.get("review_artifacts", [])
    if not isinstance(artifacts, list) or not all(isinstance(v, str) and v for v in artifacts):
        raise ValueError("review_artifacts must be a list of nonempty paths")
    digest = hashlib.sha256()
    for name in sorted(set([prompt] + artifacts)):
        digest.update(name.encode() + b"\0")
        digest.update((path.parent / name).resolve().read_bytes())
        digest.update(b"\0")
    return Policy(
        tuple(checks), tuple(command), version,
        digest.hexdigest(), timeout, limit,
    ), path.parent


def parser():
    root = argparse.ArgumentParser(
        description="Deterministic PR review lifecycle. Inspection is the default."
    )
    commands = root.add_subparsers(dest="operation", required=True)
    commands.add_parser("demo", help="Run the offline lifecycle demo; no GitHub or LLM calls")
    pilot = commands.add_parser("pilot", help="Inspect or review an offline fixture with the real worker")
    pilot.add_argument("--fixture", choices=("known-bug", "clean"), required=True)
    pilot.add_argument("--execute", action="store_true", help="Permit the real review worker")
    pilot.add_argument("--config", default="config.example.json")
    pilot.add_argument("--state", default=".dark-factory/pilot.sqlite3")
    status = commands.add_parser("status", help="Read persisted review state")
    status.add_argument("--state", default=".dark-factory/state.sqlite3")
    for operation in ("scan", "reconcile"):
        command = commands.add_parser(
            operation, help="Inspect open PRs" if operation == "scan" else "Process one PR"
        )
        command.add_argument("--repo", required=True, help="Explicit repository owner/name")
        if operation == "reconcile":
            command.add_argument("--pr", required=True, type=int)
        command.add_argument("--config", default="config.example.json")
        command.add_argument("--state", default=".dark-factory/state.sqlite3")
        command.add_argument("--execute", action="store_true", help="Permit eligible review workers")
        command.add_argument("--publish", action="store_true", help="Permit COMMENT reviews on GitHub")
        command.add_argument(
            "--retry", action="store_true",
            help="Explicitly retry a failed review or an expired review claim",
        )
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    state = None
    try:
        if args.operation == "demo":
            print(json.dumps(run_demo(), indent=2))
            return 0
        state = State(args.state)
        if args.operation == "status":
            print(json.dumps({
                "pull_requests": state.observations(), "reviews": state.list()
            }, indent=2))
            return 0
        policy, project = load_policy(args.config)
        if args.execute and not policy.review_command:
            raise ValueError("--execute requires a review_command")
        reviewer = CommandReviewer(policy, Path(args.state).parent / "runs", project)
        if args.operation == "pilot":
            from .pilot import FixtureGitHub
            github = FixtureGitHub(project / "examples/reviews" / (args.fixture + ".json"))
            controller = Controller(github, state, policy, reviewer)
            result = controller.reconcile(github.current.number, execute=args.execute)
            print(json.dumps(dict(result, mode="offline_fixture_real_worker"), indent=2))
            return 0
        github = GitHub(args.repo)
        controller = Controller(github, state, policy, reviewer)
        numbers = (
            sorted(set(github.open_prs()) | set(state.active_prs(args.repo)))
            if args.operation == "scan" else [args.pr]
        )
        results, errors = [], False
        for number in numbers:
            try:
                result = controller.reconcile(
                    number, execute=args.execute, publish=args.publish, retry=args.retry
                )
            except Exception as error:
                errors = True
                result = {"repo": args.repo, "pr": number, "action": "error", "error": str(error)}
            results.append(result)
        print(json.dumps(results, indent=2))
        return 1 if errors else 0
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 1
    finally:
        if state:
            state.close()
