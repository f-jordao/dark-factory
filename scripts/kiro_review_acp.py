"""Start the native Kiro ACP worker with a project-controlled, tool-free profile."""

import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path


def prepare_workspace(workspace, profile_path):
    workspace = Path(workspace).resolve()
    source = Path(profile_path).resolve()
    profile = json.loads(source.read_text())
    if (
        profile.get("tools") != []
        or profile.get("resources") != []
        or profile.get("mcpServers") != {}
        or profile.get("hooks") != []
        or profile.get("includeMcpJson") is not False
        or profile.get("includePowers") is not False
        or profile.get("permissions") != {
            "rules": [{"capability": "all", "match": ["**"], "effect": "deny"}]
        }
    ):
        raise ValueError("The packet-only reviewer requires its tool-free profile")
    target = workspace / ".kiro/agents/dark-factory-reviewer.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != source.read_bytes():
        raise ValueError("Refusing to overwrite a different workspace reviewer profile")
    if target != source:
        shutil.copyfile(source, target)


class ModeSelection:
    """Hold session/new until the native ACP reviewer mode is selected."""

    def __init__(self, mode="dark-factory-reviewer"):
        self.mode = mode
        self.sessions = set()
        self.pending = {}

    def client_message(self, message):
        if message.get("method") == "session/new":
            self.sessions.add(message["id"])
        return message

    def agent_message(self, message):
        if message.get("method") == "session/request_permission":
            return ("agent", {
                "jsonrpc": "2.0", "id": message["id"],
                "result": {"outcome": {"outcome": "cancelled"}},
            })
        identity = message.get("id")
        if identity in self.pending:
            original = self.pending.pop(identity)
            if "error" in message:
                raise RuntimeError("Kiro refused the review agent mode")
            original["result"]["modes"]["currentModeId"] = self.mode
            return "client", original
        if identity in self.sessions:
            self.sessions.remove(identity)
            if "error" in message:
                return "client", message
            result = message["result"]
            modes = result.get("modes", {}).get("availableModes", [])
            if self.mode not in [mode["id"] for mode in modes]:
                raise RuntimeError("Kiro did not expose the requested workspace review agent")
            private_id = "dark-factory-mode-" + result["sessionId"]
            self.pending[private_id] = message
            return ("agent", {
                "jsonrpc": "2.0", "id": private_id, "method": "session/set_mode",
                "params": {"sessionId": result["sessionId"], "modeId": self.mode},
            })
        return "client", message


async def proxy(kiro):
    selection = ModeSelection()
    process = await asyncio.create_subprocess_exec(
        kiro, "acp", "--agent-engine", "v3",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        limit=16_000_000,
    )
    client = asyncio.StreamReader(limit=16_000_000)
    await asyncio.get_running_loop().connect_read_pipe(
        lambda: asyncio.StreamReaderProtocol(client), sys.stdin.buffer
    )

    async def agent_write(message):
        process.stdin.write((json.dumps(message) + "\n").encode())
        await process.stdin.drain()

    async def client_to_agent():
        while True:
            line = await client.readline()
            if not line:
                return
            await agent_write(selection.client_message(json.loads(line)))

    async def agent_to_client():
        while True:
            line = await process.stdout.readline()
            if not line:
                return
            direction, message = selection.agent_message(json.loads(line))
            if direction == "agent":
                await agent_write(message)
            else:
                sys.stdout.write(json.dumps(message) + "\n")
                sys.stdout.flush()

    tasks = [asyncio.create_task(client_to_agent()), asyncio.create_task(agent_to_client())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()


def main():
    kiro = shutil.which("kiro-cli")
    if not kiro:
        raise SystemExit("Kiro CLI is not installed on the Fabro worker machine")
    project = Path(__file__).resolve().parent.parent
    prepare_workspace(Path.cwd(), project / "workers/kiro/reviewer.json")
    configured = subprocess.run(
        [kiro, "settings", "--workspace", "chat.disableInheritingDefaultResources", "true"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if configured.returncode:
        raise SystemExit("Could not disable inherited Kiro resources in the review workspace")
    asyncio.run(proxy(kiro))


if __name__ == "__main__":
    main()
