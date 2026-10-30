"""Register disabled scaffold definitions in the project-local Fabro Automations UI."""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
from dark_factory.workflows import load_catalog, validate_catalog


def automation_definitions(project, repository, revision):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Repository must be owner/name")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Pin the scaffold registration to a full Git commit SHA")
    validate_catalog(project)
    catalog, _, _ = load_catalog(project)
    return [{
        "id": "dark-factory-" + item["id"],
        "name": item["name"],
        "description": (
            "Dark Factory scaffold · " + item["description"]
            + " Content pending; execution disabled. managed-by:dark-factory/workflow-scaffold"
        ),
        "target": {
            "repository": repository, "ref": revision,
            "workflow": str(Path(item["definition"]).parent / "workflow.toml"),
        },
        "triggers": [{"id": "manual", "type": "api", "enabled": False}],
    } for item in catalog["workflows"]]


class Registry:
    def __init__(self, project):
        runtime = Path(project) / ".dark-factory/runtime"
        self.url = (runtime / "server-url").read_text().strip()
        if not re.fullmatch(r"http://127\.0\.0\.1:\d+", self.url):
            raise ValueError("Only the authenticated project-local Fabro server is supported")
        self.token = (runtime / "dev-token").read_text().strip()

    def request(self, path, payload=None):
        headers = {"Authorization": "Bearer " + self.token}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.url + "/api/v1/" + path, headers=headers,
            data=None if payload is None else json.dumps(payload).encode(),
            method="GET" if payload is None else "POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError("Fabro registration returned HTTP " + str(error.code)) from error


def register(registry, definitions):
    # Inspect all conflicts before creating anything. Never rewrite an existing automation.
    existing = {item["id"]: item for item in registry.request("automations")["data"]}
    for expected in definitions:
        current = existing.get(expected["id"])
        if current is not None and any(current.get(key) != value for key, value in expected.items()):
            raise ValueError("Existing automation differs; left untouched: " + expected["id"])
    actions = []
    for expected in definitions:
        if expected["id"] in existing:
            actions.append({"id": expected["id"], "action": "unchanged"})
            continue
        created = registry.request("automations", expected)
        if any(created.get(key) != value for key, value in expected.items()):
            raise RuntimeError("Fabro stored a different definition: " + expected["id"])
        actions.append({"id": expected["id"], "action": "created"})
    persisted = {item["id"]: item for item in registry.request("automations")["data"]}
    for expected in definitions:
        stored = persisted.get(expected["id"], {})
        if any(stored.get(key) != value for key, value in expected.items()):
            raise RuntimeError("Registration verification failed: " + expected["id"])
    return {"automations": actions, "execution_enabled": False,
            "schedules_created": 0, "agent_invocations": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="f-jordao/dark-factory")
    parser.add_argument("--ref", required=True, help="Full, published Git commit SHA")
    parser.add_argument("--apply", action="store_true", help="Save disabled definitions in local Fabro")
    args = parser.parse_args()
    try:
        definitions = automation_definitions(PROJECT, args.repository, args.ref)
        result = register(Registry(PROJECT), definitions) if args.apply else {
            "definitions": definitions, "execution_enabled": False, "agent_invocations": 0,
        }
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
