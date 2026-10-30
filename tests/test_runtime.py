import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import local_fabro


class RuntimeTests(unittest.TestCase):
    def test_repeat_setup_preserves_secrets_and_separate_environment_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            binary = runtime / "bin/fabro"
            binary.parent.mkdir()
            binary.write_text("already downloaded")
            (runtime / "server-url").write_text("http://127.0.0.1:12345")
            with patch.object(local_fabro, "RUNTIME", runtime), contextlib.redirect_stdout(io.StringIO()):
                local_fabro.setup()
                secret = (runtime / "dev-token").read_text()
                local_fabro.setup()
            self.assertEqual((runtime / "dev-token").read_text(), secret)
            self.assertEqual((runtime / "dev-token").stat().st_mode & 0o777, 0o600)
            self.assertNotIn("[environments.", (runtime / "server.toml").read_text())
            self.assertIn(
                '[server.web]\nenabled = true\nurl = "http://127.0.0.1:12345"',
                (runtime / "server.toml").read_text(),
            )
            self.assertEqual(
                (runtime / "environments/dark-factory-local.toml").read_text(),
                'provider = "local"\n',
            )

    def test_same_process_title_with_wrong_executable_cannot_be_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            (runtime / "server.pid").write_text("12345")
            (runtime / "server-url").write_text("http://127.0.0.1:12345")
            responses = [
                subprocess.CompletedProcess([], 0, stdout="fabro server tcp:127.0.0.1:12345"),
                subprocess.CompletedProcess([], 0, stdout="n/some/other/fabro\n"),
            ]
            with (
                patch.object(local_fabro, "RUNTIME", runtime),
                patch.object(local_fabro.platform, "system", return_value="Darwin"),
                patch.object(local_fabro.subprocess, "run", side_effect=responses),
                patch.object(local_fabro.os, "kill") as kill,
            ):
                with self.assertRaisesRegex(RuntimeError, "does not identify"):
                    local_fabro.stop()
                kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
