from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import requests

from config import settings

logger = logging.getLogger(__name__)


class JiraClientError(RuntimeError):
    pass


def _is_mock_mode() -> bool:
    """Use mock Jira when running locally without real credentials."""
    import os
    if os.getenv("SWARMFORGE_MOCK_EXTERNAL", "").lower() in ("1", "true", "yes"):
        return True
    if settings.APP_ENV in ("local", "test"):
        token = (settings.JIRA_API_TOKEN or "").strip()
        return token in ("", "placeholder", "dev_token", "jira_token")
    return False


@dataclass
class JiraClient:
    base_url: str
    email: str
    api_token: str
    mock: bool = field(default=False)

    @classmethod
    def from_settings(cls) -> "JiraClient":
        mock = _is_mock_mode()
        if mock:
            logger.info("Jira client running in MOCK mode (APP_ENV=%s)", settings.APP_ENV)
        return cls(
            base_url=settings.JIRA_BASE_URL.rstrip("/"),
            email=settings.JIRA_EMAIL,
            api_token=settings.JIRA_API_TOKEN,
            mock=mock,
        )

    @property
    def _auth(self) -> tuple[str, str]:
        return (self.email, self.api_token)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if self.mock:
            return self._mock_request(method, path, **kwargs)

        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.setdefault("Accept", "application/json")
        if method.upper() in {"POST", "PUT"}:
            headers.setdefault("Content-Type", "application/json")

        response = requests.request(
            method=method,
            url=url,
            auth=self._auth,
            headers=headers,
            timeout=30,
            **kwargs,
        )
        if response.status_code >= 300:
            raise JiraClientError(
                f"Jira API {method} {path} failed: {response.status_code} {response.text}"
            )
        if not response.text:
            return {}
        return response.json()

    def _mock_request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        logger.info("[MOCK JIRA] %s %s %s", method, path, str(kwargs.get("json", ""))[:200])
        now = datetime.now(UTC).isoformat()

        if "/comment" in path and method.upper() == "POST":
            return {"id": "mock-comment-001", "created": now}
        if "/comment" in path and method.upper() == "GET":
            return {"comments": []}
        if "/issue/" in path and method.upper() == "GET":
            key = path.rsplit("/", 1)[-1]
            return {
                "key": key,
                "id": "10042",
                "fields": {
                    "summary": f"[MOCK] Issue {key}",
                    "labels": ["ai-task"],
                    "description": "Mock issue for local development",
                    "status": {"name": "To Do"},
                },
            }
        if "/issue" in path and method.upper() == "POST":
            return {"id": "10099", "key": "MOCK-99"}
        if "/search" in path:
            return {"issues": []}
        if "/field" in path:
            return []
        if "/sprint" in path and method.upper() == "GET":
            return {"values": []}
        return {}

    def get_fields(self) -> list[dict[str, Any]]:
        return self._request("GET", "/rest/api/3/field")

    def create_issue(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/rest/api/3/issue", json=payload)

    def add_comment(self, issue_key: str, text: str) -> dict[str, Any]:
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": text}],
                    }
                ],
            }
        }
        return self._request("POST", f"/rest/api/3/issue/{issue_key}/comment", json=payload)

    def list_comments(
        self,
        issue_key: str,
        start_at: int = 0,
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        data = self._request(
            "GET",
            f"/rest/api/3/issue/{issue_key}/comment",
            params={"startAt": start_at, "maxResults": max_results, "orderBy": "-created"},
        )
        return data.get("comments", [])

    def get_active_sprints(self, board_id: int) -> list[dict[str, Any]]:
        data = self._request("GET", f"/rest/agile/1.0/board/{board_id}/sprint", params={"state": "active"})
        return data.get("values", [])

    def add_issues_to_sprint(self, sprint_id: int, issue_keys: list[str]) -> dict[str, Any]:
        payload = {"issues": issue_keys}
        return self._request("POST", f"/rest/agile/1.0/sprint/{sprint_id}/issue", json=payload)

    def search_issues(self, jql: str, fields: list[str] | None = None, max_results: int = 50) -> list[dict[str, Any]]:
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": ",".join(fields or ["summary", "status", "labels", "updated"]),
        }
        data = self._request("GET", "/rest/api/3/search/jql", params=params)
        return data.get("issues", [])

    def get_issue(self, issue_key: str, fields: list[str] | None = None) -> dict[str, Any]:
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
        return self._request("GET", f"/rest/api/3/issue/{issue_key}", params=params)
