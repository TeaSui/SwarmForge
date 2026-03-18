from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


class MCPClientError(RuntimeError):
    pass


class MCPClient:
    def __init__(self):
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[str] | None = None
        self._next_id = 1

    def _ensure_proc(self) -> subprocess.Popen[str]:
        if self._proc and self._proc.poll() is None:
            return self._proc
        script = Path(__file__).with_name("mcp_bridge_server.py")
        self._proc = subprocess.Popen(
            [sys.executable, str(script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._call_unlocked("initialize", {})
        return self._proc

    def _call_unlocked(self, method: str, params: dict[str, Any]) -> Any:
        proc = self._ensure_proc()
        request_id = self._next_id
        self._next_id += 1
        request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}

        if not proc.stdin or not proc.stdout:
            raise MCPClientError("mcp bridge process streams unavailable")

        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()

        line = proc.stdout.readline()
        if not line:
            err = ""
            if proc.stderr:
                err = proc.stderr.read().strip()
            raise MCPClientError(f"mcp bridge returned no response {err}".strip())
        payload = json.loads(line)
        if payload.get("id") != request_id:
            raise MCPClientError("mcp response id mismatch")
        if "error" in payload:
            raise MCPClientError(str(payload["error"].get("message", "unknown error")))
        return payload.get("result")

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        with self._lock:
            return self._call_unlocked("tools/call", {"name": name, "arguments": arguments})

    def close(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            self._proc = None
