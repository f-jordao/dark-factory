"""Adapter template: requires an authenticated Fabro server and local ACP harness."""

import json
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: run_fabro_review.py INPUT_JSON OUTPUT_JSON")
    if not shutil.which("fabro"):
        raise SystemExit(
            "Fabro is not installed. Follow docs/fabro-setup.md. "
            "The offline demo and GitHub inspection do not require Fabro."
        )
    packet_path, output_path = [Path(arg).resolve() for arg in sys.argv[1:]]
    packet = json.loads(packet_path.read_text())
    project = Path(__file__).resolve().parent.parent
    goal_path = packet_path.with_name("goal.txt")
    goal_path.write_text(
        "Perform a read-only review of the immutable PR packet.\n"
        "Input packet: " + str(packet_path) + "\n"
        "Output JSON: " + str(output_path) + "\n"
        "Repository: " + packet["repo"] + "\n"
        "PR: " + str(packet["pr_number"]) + "\n"
        "Head SHA: " + packet["head_sha"] + "\n"
        "Base SHA: " + packet["base_sha"] + "\n"
        "Write the output file. Do not publish, approve, merge or execute PR code.\n"
    )
    result = subprocess.run(
        ["fabro", "run", str(project / "workflows/pr-review/workflow.toml"),
         "--goal-file", str(goal_path)],
        cwd=project,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
