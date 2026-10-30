"""A deterministic ACP peer that waits for cancellation; never invokes a model."""

import json
import os
import signal
import sys
from pathlib import Path


root = Path.cwd()
(root / "fixture.pid").write_text(str(os.getpid()))
pending = None


def stopped(signum, frame):
    (root / "fixture.terminated").write_text("SIGTERM")
    raise SystemExit(0)


signal.signal(signal.SIGTERM, stopped)
try:
    for line in sys.stdin:
        message = json.loads(line)
        method = message.get("method")
        result = None
        if method == "initialize":
            result = {"protocolVersion": 1, "agentCapabilities": {}}
        elif method == "session/new":
            result = {"sessionId": "cancel-fixture"}
        elif method == "session/prompt":
            pending = message["id"]
            (root / "fixture.prompted").write_text("waiting")
        elif method == "session/cancel":
            (root / "fixture.cancelled").write_text("session/cancel")
            print(json.dumps({
                "jsonrpc": "2.0", "id": pending, "result": {"stopReason": "cancelled"},
            }), flush=True)
            break
        if result is not None:
            print(json.dumps({
                "jsonrpc": "2.0", "id": message["id"], "result": result,
            }), flush=True)
finally:
    (root / "fixture.exited").write_text("exited")
