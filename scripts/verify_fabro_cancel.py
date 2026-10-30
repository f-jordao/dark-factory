"""Opt-in integration check: a real Fabro server, a fake ACP peer, zero LLM calls."""

import json
import os
import sys
import time
import uuid
from pathlib import Path
from unittest.mock import patch


def main():
    project = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project))
    from dark_factory.fabro import LocalFabro, prepare_workflow
    directory = project / ".dark-factory/runs" / ("cancel-check-" + uuid.uuid4().hex)
    directory.mkdir(parents=True, mode=0o700)
    input_path = directory / "input.json"
    input_path.write_bytes((project / "examples/reviews/known-bug.json").read_bytes())

    def fake_workflow(project, attempt, packet):
        config = prepare_workflow(project, attempt, packet)
        graph = config.with_name("workflow.fabro")
        graph.write_text(graph.read_text().replace(
            str(project / "scripts/kiro_review_acp.py"),
            str(project / "tests/fixtures/acp_wait.py"),
        ))
        return config

    worker = LocalFabro(project, timeout=8)
    with patch("dark_factory.fabro.prepare_workflow", side_effect=fake_workflow):
        try:
            worker.review(input_path, directory / "output.json")
        except TimeoutError:
            pass
        else:
            raise RuntimeError("Expected an interrupted review")
    attempt = worker.metadata_path.parent
    if not (attempt / "fixture.prompted").exists():
        raise RuntimeError("Fixture never reached the waiting work stage")
    if not worker.metadata.get("cancellation_confirmed"):
        raise RuntimeError("Fabro did not confirm a terminal run")
    pid = int((attempt / "fixture.pid").read_text())
    deadline = time.monotonic() + 5
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError("Cancelled ACP process is still alive")
        time.sleep(0.1)
    print(json.dumps({
        "run_id": worker.run_id, "cancellation_confirmed": True,
        "status": worker.metadata["status"], "worker_stopped": True, "llm_calls": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
