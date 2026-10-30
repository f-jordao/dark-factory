import contextlib
import copy
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dark_factory.cli import main
from dark_factory.workflows import (
    build_catalog, load_catalog, project_path, select_route, validate_catalog,
)
from scripts.register_workflows import automation_definitions, register

PROJECT = Path(__file__).resolve().parent.parent


class FakeRegistry:
    def __init__(self, existing=()):
        self.items = {item["id"]: copy.deepcopy(item) for item in existing}
        self.posts = []

    def request(self, path, payload=None):
        if path != "automations":
            raise AssertionError("Registration must never request a run or start endpoint")
        if payload is None:
            return {"data": list(self.items.values())}
        self.posts.append(copy.deepcopy(payload))
        result = dict(payload, revision="a" * 64)
        self.items[payload["id"]] = result
        return result


class WorkflowCatalogTests(unittest.TestCase):
    def test_all_demand_routes_and_shared_flows_are_disabled_and_valid(self):
        report = validate_catalog(PROJECT)
        self.assertEqual(len(report["workflows"]), 13)
        self.assertFalse(report["execution_enabled"])
        self.assertEqual(report["agent_invocations"], 0)
        catalog, stages, definitions = load_catalog(PROJECT)
        for item in catalog["workflows"]:
            graph = (PROJECT / Path(item["definition"]).parent / "workflow.fabro").read_text()
            self.assertIn('label="Content pending — execution blocked"', graph)
            self.assertIn("exit 78", graph)
            self.assertIn(
                'scaffold_guard -> exit [label="Content pending"]',
                graph,
            )
            guard_progress = [line for line in graph.splitlines()
                              if "scaffold_guard -> " in line and " -> exit" not in line]
            self.assertEqual(len(guard_progress), 1)
            self.assertIn('condition="outcome=succeeded"', guard_progress[0])
            self.assertNotIn('acp.command="kiro-cli', graph)
            for node in definitions[item["id"]]["nodes"]:
                if stages[node["stage"]]["executor"] == "agent":
                    self.assertIsNone(stages[node["stage"]]["worker_binding"])

    def test_risk_overrides_demand_category_and_incomplete_evidence(self):
        cases = [
            ("bug", "local", False, False, "R1"),
            ("bug", "local", False, True, "R2"),
            ("bug", "service", False, False, "R2"),
            ("maintenance", "shared", False, False, "R2"),
            ("feature", "local", False, False, "R2"),
            ("bug", "local", True, False, "R3"),
            ("maintenance", "system", False, False, "R3"),
            ("security", "local", False, False, "R3"),
            ("incident", "local", False, True, "R3"),
            ("discovery", "system", True, True, "Discovery"),
        ]
        for demand, radius, sensitive, incomplete, expected in cases:
            with self.subTest(demand=demand, radius=radius, sensitive=sensitive):
                result = select_route(PROJECT, demand, radius, sensitive, incomplete)
                self.assertEqual(result["risk_class"], expected)
                self.assertFalse(result["execution_enabled"])
                self.assertEqual(result["agent_invocations"], 0)
        self.assertEqual(select_route(PROJECT, "exploration")["workflow"], "discovery")
        for demand, radius in [("unknown", "local"), ("bug", "unknown")]:
            with self.assertRaises(ValueError):
                select_route(PROJECT, demand, radius)
        with self.assertRaises(ValueError):
            select_route(PROJECT, "bug", sensitive="false")

    def test_discovery_cannot_reach_implementation_or_merge(self):
        _, stages, definitions = load_catalog(PROJECT)
        discovery = definitions["discovery"]
        agent_stages = [node["stage"] for node in discovery["nodes"]
                        if stages[node["stage"]]["executor"] == "agent"]
        self.assertNotIn("implement", agent_stages)
        self.assertFalse(any(node.get("workflow") == "merge-readiness"
                             for node in discovery["nodes"]))

    def _copy(self, directory):
        project = Path(directory)
        for name in ("workflows", "stages", "policy"):
            shutil.copytree(PROJECT / name, project / name)
        return project

    def _mutate(self, project, path, mutation):
        target = project / path
        data = json.loads(target.read_text())
        mutation(data)
        target.write_text(json.dumps(data))

    def test_missing_stage_and_unreachable_stage_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy(directory)
            self._mutate(project, "workflows/discovery/definition.json",
                         lambda flow: flow["nodes"].append({"id": "lost", "stage": "implement"}))
            with self.assertRaisesRegex(ValueError, "Unreachable"):
                validate_catalog(project, generated=False)
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy(directory)
            self._mutate(project, "workflows/discovery/definition.json",
                         lambda flow: flow["nodes"][0].update(stage="missing"))
            with self.assertRaisesRegex(ValueError, "Unknown stage"):
                validate_catalog(project, generated=False)

    def test_missing_conditional_fallback_and_unbound_approval_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy(directory)
            def remove_fallback(flow):
                for edge in flow["edges"]:
                    if edge["from"] == "eligible" and "condition" not in edge:
                        edge["condition"] = "context.review_eligible=false"
            self._mutate(project, "workflows/pr-review-lifecycle/definition.json", remove_fallback)
            with self.assertRaisesRegex(ValueError, "one fallback"):
                validate_catalog(project, generated=False)
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy(directory)
            def weaken_approval(flow):
                for node in flow["nodes"]:
                    if node.get("approval"):
                        node["record_fields"].remove("scope_digest")
                        break
            self._mutate(project, "workflows/discovery/definition.json", weaken_approval)
            with self.assertRaisesRegex(ValueError, "Approval must be bound"):
                validate_catalog(project, generated=False)

    def test_modified_generated_graph_is_detected_and_rebuild_restores_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy(directory)
            target = project / "workflows/discovery/workflow.fabro"
            target.write_text(target.read_text().replace("exit 78", "exit 0"))
            with self.assertRaisesRegex(ValueError, "stale"):
                validate_catalog(project)
            build_catalog(project)
            self.assertTrue(validate_catalog(project)["valid"])
            self.assertIn("exit 78", target.read_text())

    def test_project_paths_cannot_escape_even_through_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "outside").symlink_to(PROJECT.parent, target_is_directory=True)
            for relative in ["../secret", "/absolute", "outside/secret"]:
                with self.assertRaises(ValueError):
                    project_path(project, relative)

    def test_inspection_does_not_open_controller_state_or_execute_a_worker(self):
        with patch("dark_factory.cli.State") as state, \
                patch("dark_factory.cli.CommandReviewer") as worker, \
                patch("dark_factory.cli.GitHub") as github, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["workflows", "list"]), 0)
            self.assertEqual(main(["workflows", "route", "--demand", "feature"]), 0)
            self.assertEqual(main(["workflows", "show", "discovery"]), 0)
            state.assert_not_called()
            worker.assert_not_called()
            github.assert_not_called()


class WorkflowRegistrationTests(unittest.TestCase):
    def definitions(self):
        return automation_definitions(PROJECT, "f-jordao/dark-factory", "b" * 40)

    def test_registration_is_disabled_and_repeat_does_not_duplicate_or_start_runs(self):
        registry = FakeRegistry()
        definitions = self.definitions()
        first = register(registry, definitions)
        second = register(registry, definitions)
        self.assertEqual(len(registry.posts), 13)
        self.assertTrue(all(item["action"] == "created" for item in first["automations"]))
        self.assertTrue(all(item["action"] == "unchanged" for item in second["automations"]))
        for item in registry.posts:
            self.assertEqual(item["triggers"], [{"id": "manual", "type": "api", "enabled": False}])
            self.assertEqual(item["target"]["ref"], "b" * 40)
        self.assertEqual(first["schedules_created"], 0)
        self.assertEqual(first["agent_invocations"], 0)

    def test_existing_enabled_or_changed_definition_is_preserved_without_partial_registration(self):
        definitions = self.definitions()
        existing = copy.deepcopy(definitions[-1])
        existing["triggers"][0]["enabled"] = True
        registry = FakeRegistry([existing])
        before = copy.deepcopy(registry.items)
        with self.assertRaisesRegex(ValueError, "left untouched"):
            register(registry, definitions)
        self.assertEqual(registry.posts, [])
        self.assertEqual(registry.items, before)

    def test_remote_target_must_use_an_immutable_revision(self):
        with self.assertRaisesRegex(ValueError, "full Git commit"):
            automation_definitions(PROJECT, "f-jordao/dark-factory", "main")


if __name__ == "__main__":
    unittest.main()
