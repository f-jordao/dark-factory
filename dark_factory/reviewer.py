import json
import os
import subprocess
import sys
from pathlib import Path


class CommandReviewer:
    """A single explicit work stage. The controller never runs an LLM itself."""

    def __init__(self, policy, run_directory, project_root):
        self.policy = policy
        self.run_directory = Path(run_directory).resolve()
        self.project_root = Path(project_root).resolve()

    def review(self, key, packet):
        if not self.policy.review_command:
            raise ValueError("No review command configured")
        directory = self.run_directory / key
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        input_path, output_path = directory / "input.json", directory / "output.json"
        input_path.write_text(json.dumps(packet, indent=2) + "\n")
        output_path.unlink(missing_ok=True)
        substitutions = {
            "{input}": str(input_path), "{output}": str(output_path),
            "{project}": str(self.project_root), "{python}": sys.executable,
        }
        command = []
        for argument in self.policy.review_command:
            for token, value in substitutions.items():
                argument = argument.replace(token, value)
            command.append(argument)
        environment = os.environ.copy()
        environment["DARK_FACTORY_REVIEW_TIMEOUT_SECONDS"] = str(
            max(1, self.policy.timeout_seconds - 20)
        )
        with (directory / "worker.log").open("w") as log:
            worker = subprocess.Popen(
                command, cwd=self.project_root, env=environment, stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                returncode = worker.wait(timeout=self.policy.timeout_seconds)
            except subprocess.TimeoutExpired as error:
                worker.terminate()
                try:
                    worker.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.wait()
                raise RuntimeError("Review worker timed out; see " + str(log.name)) from error
        if returncode:
            raise RuntimeError("Review worker failed; see " + str(directory / "worker.log"))
        if not output_path.is_file() or output_path.stat().st_size > 150_000:
            raise ValueError("Review worker did not produce an acceptable output.json")
        return json.loads(output_path.read_text())
