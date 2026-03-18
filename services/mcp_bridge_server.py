from __future__ import annotations

import json
import sys
from typing import Any

import requests

from config import settings
from services.jira_client import JiraClient, JiraClientError


def _extract_description(field: Any) -> str:
    if isinstance(field, str):
        return field
    if not isinstance(field, dict):
        return "No description"
    parts: list[str] = []
    for block in field.get("content", []):
        for node in block.get("content", []):
            text = node.get("text")
            if text:
                parts.append(str(text))
    return " ".join(parts) or "No description"


class MCPBridgeServer:
    def __init__(self):
        self.jira = JiraClient.from_settings()

    def _ok(self, request_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _err(self, request_id: Any, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": message}}

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        method = payload.get("method")
        request_id = payload.get("id")
        params = payload.get("params", {})

        if method == "initialize":
            return self._ok(request_id, {"name": "swarmforge-mcp-bridge", "version": "1.0.0"})
        if method == "tools/list":
            return self._ok(
                request_id,
                {
                    "tools": [
                        "jira.get_issue_details",
                        "jira.add_comment",
                        "github.search_code",
                    ]
                },
            )
        if method != "tools/call":
            return self._err(request_id, f"unsupported method: {method}")

        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            if tool_name == "jira.get_issue_details":
                issue = self.jira.get_issue(str(arguments.get("issue_key")))
                fields = issue.get("fields", {})
                return self._ok(
                    request_id,
                    {
                        "issue_key": issue.get("key"),
                        "summary": fields.get("summary", "No summary"),
                        "description": _extract_description(fields.get("description")),
                    },
                )
            if tool_name == "jira.add_comment":
                issue_key = str(arguments.get("issue_key"))
                comment = str(arguments.get("comment", ""))
                data = self.jira.add_comment(issue_key, comment)
                return self._ok(request_id, {"issue_key": issue_key, "comment_id": data.get("id")})
            if tool_name == "github.search_code":
                query = str(arguments.get("query", "")).strip()
                token = (settings.GITHUB_TOKEN or "").strip()
                if not query:
                    return self._ok(request_id, {"items": []})
                if not token:
                    return self._err(request_id, "missing github token")
                response = requests.get(
                    f"https://api.github.com/search/code?q={query}",
                    headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
                    timeout=30,
                )
                if response.status_code >= 300:
                    return self._err(request_id, f"github search failed: {response.status_code}")
                items = response.json().get("items", [])[:5]
                simplified = [
                    {
                        "repo": item.get("repository", {}).get("full_name"),
                        "path": item.get("path"),
                    }
                    for item in items
                ]
                return self._ok(request_id, {"items": simplified})
            return self._err(request_id, f"unsupported tool: {tool_name}")
        except JiraClientError as exc:
            return self._err(request_id, f"jira error: {exc}")
        except Exception as exc:
            return self._err(request_id, str(exc))


def main() -> int:
    server = MCPBridgeServer()
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = server.handle(payload)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
