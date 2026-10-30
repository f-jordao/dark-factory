"""Validate the Fabro graphs; optionally exercise the deterministic scaffold guard."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
from dark_factory.fabro import LocalFabro, status_kind
from dark_factory.workflows import load_catalog, validate_catalog


def native_validation():
    validate_catalog(PROJECT)
    catalog, _, _ = load_catalog(PROJECT)
    binary = PROJECT / ".dark-factory/runtime/bin/fabro"
    results = []
    for item in catalog["workflows"]:
        graph = PROJECT / Path(item["definition"]).parent / "workflow.fabro"
        result = subprocess.run(
            [str(binary), "validate", str(graph), "--json", "--no-upgrade-check"],
            capture_output=True, text=True, timeout=30,
        )
        validation = json.loads(result.stdout)
        if result.returncode or not validation.get("valid"):
            raise RuntimeError("Fabro graph validation failed: " + item["id"])
        results.append({"id": item["id"], "valid": True,
                        "diagnostics": validation.get("diagnostics", [])})
    return results


def guard_smoke():
    client = LocalFabro(PROJECT, timeout=30)
    created = client.cli("create", str(PROJECT / "workflows/feature-delivery/workflow.toml"))
    client.run_id = created["run_id"]
    directory = PROJECT / ".dark-factory/preview"
    directory.mkdir(parents=True, exist_ok=True)
    record = directory / "scaffold-guard-smoke.json"
    record.write_text(json.dumps({"run_id": client.run_id, "status": "submitted"}, indent=2))
    try:
        client.cli("start", client.run_id)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            run = client.api("runs/" + client.run_id)
            if status_kind(run) in {"succeeded", "failed", "dead"}:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Scaffold guard did not reach terminal state")
        stages = client.api("runs/" + client.run_id + "/stages")["data"]
        events = client.api("runs/" + client.run_id + "/events")["data"]
        if status_kind(run) != "failed":
            raise RuntimeError("Scaffold should finish failed because its content is pending")
        if any(stage["handler"] in {"agent", "prompt", "human"} for stage in stages):
            raise RuntimeError("Scaffold advanced beyond its deterministic guard")
        guard = [stage for stage in stages if stage["node_id"] == "scaffold_guard"]
        if len(guard) != 1 or guard[0]["status"] != "failed":
            raise RuntimeError("Expected exactly one failed scaffold guard")
        if any(event["event"].startswith(("agent.", "llm.", "interview.")) for event in events):
            raise RuntimeError("Scaffold emitted unexpected agent or interview activity")
        report = {
            "run_id": client.run_id, "status": status_kind(run),
            "stages": stages, "agent_invocations": 0,
        }
        record.write_text(json.dumps(report, indent=2) + "\n")
        return report
    except BaseException:
        client.cancel()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guard-smoke", action="store_true")
    args = parser.parse_args()
    report = {"validation": native_validation(), "agent_invocations": 0}
    if args.guard_smoke:
        report["guard"] = guard_smoke()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
