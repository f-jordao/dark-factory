"""Same-machine Fabro adapter: persist run identity, capture output, cancel on failure."""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from .models import validate_result


class InterruptedReview(Exception):
    pass


def status_kind(run):
    status = run["lifecycle"]["status"]
    return status["kind"] if isinstance(status, dict) else status


def parse_response(text):
    text = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", text, flags=re.DOTALL)
    return json.loads(fenced.group(1) if fenced else text)


def prepare_workflow(project, directory, packet):
    project, directory = Path(project).resolve(), Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    graph = (project / "workflows/pr-review/workflow.fabro").read_text()
    command = {
        "type": "stdio", "name": "dark-factory-reviewer",
        "command": sys.executable,
        "args": [str(project / "scripts/kiro_review_acp.py")],
    }
    old = 'acp.command="kiro-cli acp"'
    if graph.count(old) != 1:
        raise ValueError("Expected exactly one configurable ACP review command")
    graph = graph.replace(old, "acp.config=" + json.dumps(json.dumps(command)))
    prompt_directory = directory / "prompts"
    prompt_directory.mkdir(exist_ok=True)
    shutil.copyfile(project / "prompts/pr-review.md", prompt_directory / "pr-review.md")
    graph = graph.replace('"@../../prompts/pr-review.md"', '"@prompts/pr-review.md"')
    (directory / "workflow.fabro").write_text(graph)
    base = (project / "workflows/pr-review/workflow.toml").read_text()
    if "[run.inputs]" in base:
        raise ValueError("Static workflow must not override per-run packet inputs")
    config = base + "\n[run.inputs]\npacket_json = " + json.dumps(json.dumps(packet)) + "\n"
    path = directory / "workflow.toml"
    path.write_text(config)
    return path


class LocalFabro:
    def __init__(self, project, timeout=850):
        self.project = Path(project).resolve()
        self.runtime = self.project / ".dark-factory/runtime"
        pinned = self.runtime / "bin/fabro"
        candidate = os.environ.get("DARK_FACTORY_FABRO_BINARY")
        self.binary = (
            Path(candidate) if candidate else
            pinned if pinned.is_file() else Path(shutil.which("fabro") or str(pinned))
        )
        if not self.binary.is_file():
            raise ValueError("Fabro is not installed; run scripts/local_fabro.py setup")
        self.server = (self.runtime / "server-url").read_text().strip()
        if not re.fullmatch(r"http://127\.0\.0\.1:\d+", self.server):
            raise ValueError("This adapter supports the project-local loopback Fabro server")
        self.token = (self.runtime / "dev-token").read_text().strip()
        self.timeout = timeout
        self.run_id = None
        self.metadata_path = None
        self.metadata = {}
        self.workspace = self.project

    def api(self, path, method="GET"):
        request = urllib.request.Request(
            self.server + "/api/v1/" + path, method=method,
            headers={"Authorization": "Bearer " + self.token},
            data=b"" if method == "POST" else None,
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)

    def cli(self, *args):
        completed = subprocess.run(
            [str(self.binary), *args, "--server", self.server, "--no-upgrade-check", "--json"],
            capture_output=True, text=True, timeout=60, cwd=self.workspace,
        )
        if completed.returncode:
            raise RuntimeError(completed.stderr.strip() or "Fabro command failed")
        return json.loads(completed.stdout)

    def record(self, **fields):
        self.metadata.update(fields)
        if self.metadata_path:
            temporary = self.metadata_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.metadata, indent=2) + "\n")
            temporary.replace(self.metadata_path)

    def cancel(self):
        if not self.run_id:
            return
        try:
            current = self.api("runs/" + self.run_id)
            if status_kind(current) not in ("succeeded", "failed", "dead"):
                self.api("runs/" + self.run_id + "/cancel", method="POST")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                current = self.api("runs/" + self.run_id)
                if status_kind(current) in ("succeeded", "failed", "dead"):
                    self.record(cancellation_confirmed=True, status=status_kind(current))
                    return
                time.sleep(0.25)
            self.record(cancellation_confirmed=False)
        except Exception as error:
            self.record(cancellation_confirmed=False, cancellation_error=str(error))

    def review(self, input_path, output_path):
        input_path, output_path = Path(input_path).resolve(), Path(output_path).resolve()
        packet = json.loads(input_path.read_text())
        attempt = output_path.parent / ("fabro-" + uuid.uuid4().hex)
        config = prepare_workflow(self.project, attempt, packet)
        self.workspace = attempt
        self.metadata_path = attempt / "run.json"
        self.record(server=self.server, status="preparing")
        previous_handler = signal.getsignal(signal.SIGTERM)

        def interrupted(signum, frame):
            raise InterruptedReview("Review command was terminated")

        signal.signal(signal.SIGTERM, interrupted)
        try:
            created = self.cli("create", str(config))
            self.run_id = created["run_id"]
            if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", self.run_id):
                raise ValueError("Fabro returned an invalid run identity")
            self.record(run_id=self.run_id, status="created")
            self.cli("start", self.run_id)
            deadline = time.monotonic() + self.timeout
            while True:
                current = self.api("runs/" + self.run_id)
                status = status_kind(current)
                self.record(status=status)
                if status in ("succeeded", "failed", "dead"):
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError("Fabro review exceeded its time budget")
                time.sleep(0.5)
            if status != "succeeded":
                raise RuntimeError("Fabro review failed: " + json.dumps(current["lifecycle"]["error"]))
            stages = self.api("runs/" + self.run_id + "/stages")["data"]
            reviews = [stage for stage in stages if stage["node_id"] == "review"]
            if len(reviews) != 1 or reviews[0]["status"] != "succeeded":
                raise RuntimeError("Fabro run did not contain exactly one successful review stage")
            export = attempt / "export"
            self.cli("dump", self.run_id, "--output", str(export))
            responses = list(export.glob("stages/*-review@1/response.md"))
            if len(responses) != 1:
                raise ValueError("Expected exactly one review response in the Fabro export")
            result = validate_result(parse_response(responses[0].read_text()), packet)
            temporary = output_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(result, indent=2) + "\n")
            temporary.replace(output_path)
            self.record(status="succeeded", output=str(output_path))
            return result
        except BaseException as error:
            self.record(error=str(error))
            self.cancel()
            raise
        finally:
            signal.signal(signal.SIGTERM, previous_handler)
