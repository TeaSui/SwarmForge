from __future__ import annotations

import os
import subprocess
from base64 import b64encode
from pathlib import Path
from typing import Any, Dict


class GitOperations:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    def run_command(self, command: list[str], cwd: Path | None = None) -> Dict[str, Any]:
        try:
            proc = subprocess.run(
                command,
                cwd=str(cwd or self.workspace_root),
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            return {
                "command": " ".join(command),
                "returncode": 127,
                "stdout_tail": "",
                "stderr_tail": str(exc),
            }
        return {
            "command": " ".join(command),
            "returncode": proc.returncode,
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-20:]),
            "stderr_tail": "\n".join(proc.stderr.splitlines()[-20:]),
        }

    def command_exists(self, command: str) -> bool:
        probe = subprocess.run(
            ["which", command],
            cwd=str(self.workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )
        return probe.returncode == 0

    def run_first_available(
        self,
        candidates: list[list[str]],
        cwd: Path | None = None,
    ) -> Dict[str, Any]:
        for cmd in candidates:
            if not cmd:
                continue
            binary = cmd[0]
            if binary in {"python", "python3"} or self.command_exists(binary):
                result = self.run_command(cmd, cwd=cwd)
                if result["returncode"] != 127:
                    return result
        return {
            "command": "none",
            "returncode": 127,
            "stdout_tail": "",
            "stderr_tail": "no available command found",
        }

    def run_git(
        self,
        command: list[str],
        cwd: Path,
        env: dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        return {
            "command": " ".join(command[:3]),
            "returncode": proc.returncode,
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-20:]),
            "stderr_tail": "\n".join(proc.stderr.splitlines()[-20:]),
        }

    def github_auth_env(self, token: str) -> dict[str, str]:
        header = "AUTHORIZATION: basic " + b64encode(f"x-access-token:{token}".encode()).decode()
        merged = os.environ.copy()
        merged["GIT_HTTP_EXTRA_HEADER"] = header
        return merged
