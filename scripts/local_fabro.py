"""Manage a project-local Fabro server. These commands never invoke an LLM."""

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import signal
import socket
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path


PROJECT = Path(__file__).resolve().parent.parent
RUNTIME = PROJECT / ".dark-factory/runtime"
VERSION = "v0.254.0"


def health():
    if not (RUNTIME / "server-url").exists() or not (RUNTIME / "dev-token").exists():
        return False
    try:
        request = urllib.request.Request(
            (RUNTIME / "server-url").read_text().strip() + "/api/v1/runs?limit=1",
            headers={"Authorization": "Bearer " + (RUNTIME / "dev-token").read_text().strip()},
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False


def setup():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    RUNTIME.chmod(0o700)
    binary = RUNTIME / "bin/fabro"
    binary.parent.mkdir(exist_ok=True)
    if not binary.exists():
        system, machine = platform.system(), platform.machine()
        targets = {
            ("Darwin", "arm64"): "aarch64-apple-darwin",
            ("Linux", "aarch64"): "aarch64-unknown-linux-gnu",
            ("Linux", "x86_64"): "x86_64-unknown-linux-gnu",
        }
        target = targets.get((system, machine))
        if not target:
            raise ValueError("Unsupported platform for this pinned Fabro build")
        archive_name = "fabro-" + target + ".tar.gz"
        downloads = RUNTIME / "downloads"
        downloads.mkdir(exist_ok=True)
        subprocess.run(
            ["gh", "release", "download", VERSION, "--repo", "fabro-sh/fabro",
             "--pattern", archive_name + "*", "--dir", str(downloads), "--clobber"],
            check=True,
        )
        archive = downloads / archive_name
        expected = (downloads / (archive_name + ".sha256")).read_text().split()[0]
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise ValueError("Fabro archive checksum does not match")
        with tarfile.open(archive) as contents:
            members = [
                member for member in contents.getmembers()
                if member.isfile() and Path(member.name).name == "fabro"
            ]
            if len(members) != 1:
                raise ValueError("Expected one Fabro binary in the release archive")
            binary.write_bytes(contents.extractfile(members[0]).read())
        binary.chmod(0o755)
    for name, prefix in (("dev-token", "fabro_dev_"), ("session-secret", "")):
        secret = RUNTIME / name
        if not secret.exists():
            secret.write_text(prefix + secrets.token_hex(32))
        secret.chmod(0o600)
    if not (RUNTIME / "server-url").exists():
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        (RUNTIME / "server-url").write_text("http://127.0.0.1:" + str(port))
    address = (RUNTIME / "server-url").read_text().strip().removeprefix("http://")
    if not re.fullmatch(r"127\.0\.0\.1:\d+", address):
        raise ValueError("Project server must bind to loopback")
    environments = RUNTIME / "environments"
    environments.mkdir(exist_ok=True)
    environment_file = environments / "dark-factory-local.toml"
    environment = 'provider = "local"\n'
    if environment_file.exists() and environment_file.read_text() != environment:
        raise ValueError("Project-local environment has a different configuration")
    environment_file.write_text(environment)
    config = (
        '_version = 1\n'
        '[server.listen]\ntype = "tcp"\naddress = ' + json.dumps(address) + '\n'
        '[server.auth]\nmethods = ["dev-token"]\n'
        '[server.web]\nenabled = false\n'
        '[server.storage]\nroot = ' + json.dumps(str(RUNTIME / "storage")) + '\n'
        '[server.sandbox.providers.local]\nenabled = true\n'
    )
    (RUNTIME / "server.toml").write_text(config)
    print("Project-local Fabro runtime is configured.")


def start():
    if not health():
        setup()
        environment = os.environ.copy()
        environment["FABRO_DEV_TOKEN"] = (RUNTIME / "dev-token").read_text().strip()
        environment["SESSION_SECRET"] = (RUNTIME / "session-secret").read_text().strip()
        environment["FABRO_NO_UPGRADE_CHECK"] = "1"
        with (RUNTIME / "server.log").open("a") as log:
            process = subprocess.Popen(
                [str(RUNTIME / "bin/fabro"), "server", "start", "--foreground",
                 "--no-web", "--config", str(RUNTIME / "server.toml")],
                env=environment, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        (RUNTIME / "server.pid").write_text(str(process.pid))
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if health():
                break
            if process.poll() is not None:
                raise RuntimeError("Fabro startup failed; see .dark-factory/runtime/server.log")
            time.sleep(0.2)
        else:
            process.terminate()
            raise RuntimeError("Fabro did not become healthy")
    login = subprocess.run(
        [str(RUNTIME / "bin/fabro"), "auth", "login",
         "--server", (RUNTIME / "server-url").read_text().strip(),
         "--dev-token", (RUNTIME / "dev-token").read_text().strip(),
         "--no-upgrade-check"],
        capture_output=True, text=True, timeout=20,
    )
    if login.returncode:
        raise RuntimeError("Fabro CLI authentication failed")
    print("Project-local Fabro server is running and its CLI is authenticated.")


def stop():
    path = RUNTIME / "server.pid"
    if not path.exists():
        print("No project-local Fabro process is recorded.")
        return
    pid = int(path.read_text())
    command = subprocess.run(
        ["ps", "-p", str(pid), "-o", "args="], capture_output=True, text=True, check=False
    ).stdout
    if not command.strip():
        path.unlink()
        print("The recorded project-local server has already stopped.")
        return
    # Fabro replaces its process title after startup, so the original argv is lost.
    binary = RUNTIME / "bin/fabro"
    if platform.system() == "Linux":
        executable_matches = Path("/proc") / str(pid) / "exe"
        executable_matches = executable_matches.resolve() == binary.resolve()
    else:
        lsof = shutil.which("lsof") or "/usr/sbin/lsof"
        files = subprocess.run(
            [lsof, "-a", "-p", str(pid), "-d", "txt", "-Fn"],
            capture_output=True, text=True, check=False,
        ).stdout.splitlines()
        executable_matches = "n" + str(binary.resolve()) in files
    address = (RUNTIME / "server-url").read_text().strip().removeprefix("http://")
    original_argv = str(binary) in command and str(RUNTIME / "server.toml") in command
    process_title = command.strip() == "fabro server tcp:" + address
    if not executable_matches or not (original_argv or process_title):
        raise RuntimeError("Recorded PID does not identify this project's Fabro server")
    os.kill(pid, signal.SIGTERM)
    path.unlink()
    print("Stopped the project-local Fabro server.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("setup", "start", "status", "stop"))
    args = parser.parse_args()
    if args.action == "status":
        print(json.dumps({"running": health()}))
    else:
        {"setup": setup, "start": start, "stop": stop}[args.action]()


if __name__ == "__main__":
    main()
