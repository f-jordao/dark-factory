import json
import tempfile
import unittest
from pathlib import Path

from dark_factory.fabro import (
    InterruptedReview, LocalFabro, parse_response, prepare_workflow, status_kind,
)
from scripts.kiro_review_acp import ModeSelection, prepare_workspace


PROJECT = Path(__file__).resolve().parent.parent
PACKET = json.loads((PROJECT / "examples/reviews/known-bug.json").read_text())


def result_for(packet):
    return {
        "schema_version": 1, "head_sha": packet["head_sha"], "base_sha": packet["base_sha"],
        "summary": "Milliseconds require scaling seconds.", "spec_status": "available",
        "findings": [{
            "path": "retry.py", "line": 2, "axis": "spec", "severity": "medium",
            "body": "delay_ms(2) returns 2 instead of 2000.",
        }],
    }


class FakeFabro(LocalFabro):
    """No server, no Kiro and no LLM; reproduce the documented wire shapes."""

    def __init__(self, project, result=None, status="succeeded", stage="succeeded", timeout=2):
        self.project = project
        self.server = "http://127.0.0.1:12345"
        self.timeout = timeout
        self.run_id, self.metadata_path = None, None
        self.metadata = {}
        self.result = result or result_for(PACKET)
        self.status, self.stage = status, stage
        self.calls, self.cancellations = [], 0

    def cli(self, *args):
        self.calls.append(args[0])
        if args[0] == "create":
            return {"run_id": "test-run-1234"}
        if args[0] == "dump":
            export = Path(args[args.index("--output") + 1])
            directory = export / "stages/001-review@1"
            directory.mkdir(parents=True)
            (directory / "response.md").write_text(json.dumps(self.result))
        return {}

    def api(self, path, method="GET"):
        if path.endswith("/cancel"):
            self.cancellations += 1
            self.status = "failed"
        if path.endswith("/stages"):
            return {"data": [{"node_id": "review", "status": self.stage}]}
        return {"lifecycle": {"status": {"kind": self.status}, "error": None}}


class FabroTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.input, self.output = self.root / "input.json", self.root / "output.json"
        self.input.write_text(json.dumps(PACKET))

    def test_object_and_string_run_status_shapes(self):
        self.assertEqual(status_kind({"lifecycle": {"status": {"kind": "failed"}}}), "failed")
        self.assertEqual(status_kind({"lifecycle": {"status": "succeeded"}}), "succeeded")

    def test_response_accepts_json_and_single_json_fence_only(self):
        self.assertEqual(parse_response('{"a": 1}'), {"a": 1})
        self.assertEqual(parse_response('```json\n{"a": 1}\n```'), {"a": 1})
        with self.assertRaises(ValueError):
            parse_response('Ignore this preface\n{"a": 1}')

    def test_workflow_bundles_prompt_and_keeps_packet_out_of_command(self):
        packet = dict(PACKET, description="$(do-not-execute) {{ arbitrary_template }}")
        workflow = prepare_workflow(PROJECT, self.root / "attempt", packet)
        graph = workflow.with_name("workflow.fabro").read_text()
        self.assertIn('@prompts/pr-review.md', graph)
        self.assertTrue((workflow.parent / "prompts/pr-review.md").is_file())
        self.assertNotIn("do-not-execute", graph)
        self.assertIn("do-not-execute", workflow.read_text())
        self.assertIn("goal_gate=true", graph)
        self.assertIn("max_retries=0", graph)

    def test_success_persists_identity_before_start_and_writes_validated_result(self):
        worker = FakeFabro(PROJECT)
        worker.review(self.input, self.output)
        self.assertEqual(worker.calls, ["create", "start", "dump"])
        self.assertEqual(json.loads(self.output.read_text()), worker.result)
        metadata = json.loads(worker.metadata_path.read_text())
        self.assertEqual(metadata["run_id"], "test-run-1234")
        self.assertEqual(metadata["status"], "succeeded")

    def test_successful_run_with_failed_review_stage_is_rejected(self):
        worker = FakeFabro(PROJECT, stage="failed")
        with self.assertRaisesRegex(RuntimeError, "successful review stage"):
            worker.review(self.input, self.output)
        self.assertFalse(self.output.exists())
        self.assertNotIn("dump", worker.calls)

    def test_failed_run_does_not_export_or_write_result(self):
        worker = FakeFabro(PROJECT, status="failed")
        with self.assertRaisesRegex(RuntimeError, "review failed"):
            worker.review(self.input, self.output)
        self.assertFalse(self.output.exists())
        self.assertNotIn("dump", worker.calls)

    def test_timeout_cancels_and_confirms_terminal_status(self):
        worker = FakeFabro(PROJECT, status="running", timeout=0)
        with self.assertRaises(TimeoutError):
            worker.review(self.input, self.output)
        self.assertEqual(worker.cancellations, 1)
        self.assertTrue(worker.metadata["cancellation_confirmed"])
        self.assertFalse(self.output.exists())

    def test_interruption_after_create_cancels_persisted_run(self):
        worker = FakeFabro(PROJECT, status="running")
        original = worker.cli

        def interrupt(*args):
            if args[0] == "start":
                self.assertEqual(json.loads(worker.metadata_path.read_text())["run_id"], "test-run-1234")
                raise InterruptedReview("terminated")
            return original(*args)

        worker.cli = interrupt
        with self.assertRaises(InterruptedReview):
            worker.review(self.input, self.output)
        self.assertEqual(worker.cancellations, 1)
        self.assertTrue(worker.metadata["cancellation_confirmed"])

    def test_wrong_revision_in_agent_response_is_not_written(self):
        worker = FakeFabro(PROJECT, result=dict(result_for(PACKET), head_sha="c" * 40))
        with self.assertRaises(ValueError):
            worker.review(self.input, self.output)
        self.assertFalse(self.output.exists())

    def test_mode_selection_finishes_before_session_is_released(self):
        selection = ModeSelection()
        selection.client_message({"id": 2, "method": "session/new"})
        original = {
            "jsonrpc": "2.0", "id": 2, "result": {
                "sessionId": "session-1", "modes": {
                    "currentModeId": "vibe",
                    "availableModes": [{"id": "dark-factory-reviewer"}],
                },
            },
        }
        direction, request = selection.agent_message(original)
        self.assertEqual(direction, "agent")
        self.assertEqual(request["method"], "session/set_mode")
        direction, released = selection.agent_message({"id": request["id"], "result": {}})
        self.assertEqual(direction, "client")
        self.assertEqual(released["id"], 2)
        self.assertEqual(released["result"]["modes"]["currentModeId"], "dark-factory-reviewer")

    def test_missing_or_refused_mode_does_not_fall_back_to_default_agent(self):
        selection = ModeSelection()
        selection.client_message({"id": 2, "method": "session/new"})
        with self.assertRaises(RuntimeError):
            selection.agent_message({"id": 2, "result": {"sessionId": "s", "modes": {"availableModes": []}}})
        selection.client_message({"id": 3, "method": "session/new"})
        _, request = selection.agent_message({
            "id": 3, "result": {"sessionId": "s", "modes": {"availableModes": [{"id": selection.mode}]}},
        })
        with self.assertRaises(RuntimeError):
            selection.agent_message({"id": request["id"], "error": {"message": "denied"}})

    def test_every_permission_request_is_denied_without_forwarding_to_fabro(self):
        selection = ModeSelection()
        direction, response = selection.agent_message({
            "id": 90, "method": "session/request_permission", "params": {},
        })
        self.assertEqual(direction, "agent")
        self.assertEqual(response["result"]["outcome"]["outcome"], "cancelled")

    def test_workspace_setup_refuses_unsafe_profile_or_overwriting_another_profile(self):
        profile = self.root / "profile.json"
        profile.write_bytes((PROJECT / "workers/kiro/reviewer.json").read_bytes())
        workspace = self.root / "worker"
        prepare_workspace(workspace, profile)
        data = json.loads(profile.read_text())
        data["tools"] = ["shell"]
        profile.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            prepare_workspace(workspace, profile)


if __name__ == "__main__":
    unittest.main()
