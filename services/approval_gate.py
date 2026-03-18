from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict

from config import settings
from services.jira_client import JiraClient, JiraClientError

logger = logging.getLogger(__name__)

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"

class ApprovalGate:
    """Human-in-the-loop approval via Jira comments."""

    def __init__(self, state_manager: Any):
        self.state_manager = state_manager
        self.jira_client = JiraClient.from_settings()
        self.poll_interval_seconds = max(
            2, int(getattr(settings, "APPROVAL_POLL_INTERVAL_SECONDS", 15))
        )
        self.timeout_seconds = max(
            30, int(getattr(settings, "APPROVAL_TIMEOUT_SECONDS", 900))
        )

    def _comment_to_text(self, comment: Dict[str, Any]) -> str:
        body = comment.get("body", {})
        chunks: list[str] = []
        for block in body.get("content", []):
            for node in block.get("content", []):
                text = node.get("text")
                if text:
                    chunks.append(str(text))
        return " ".join(chunks).strip().lower()

    def _is_approval_signal(self, text: str) -> str | None:
        if "/approve" in text:
            return ApprovalStatus.APPROVED.value
        if "/reject" in text:
            return ApprovalStatus.REJECTED.value
        return None

    async def request_approval(self, task_id: str, action_type: str, details: Dict[str, Any]) -> str:
        issue_key = str(details.get("jira_issue_key") or task_id)
        requested_at = datetime.now(UTC)
        logger.warning(
            "Approval required for task_id=%s issue=%s action=%s",
            task_id,
            issue_key,
            action_type,
        )

        await self.state_manager.update_state(
            task_id,
            "APPROVAL_NEEDED",
            metadata={
                "sub_state": "APPROVAL_REQUESTED",
                "action": action_type,
                "details": details,
            },
        )

        try:
            self.jira_client.add_comment(
                issue_key,
                (
                    f"[SwarmForge] Approval needed for critical stage `{action_type}`. "
                    f"Reply with `/approve` or `/reject`."
                ),
            )
        except JiraClientError as exc:
            logger.error("Failed to post Jira approval comment for %s: %s", issue_key, exc)
            return ApprovalStatus.REJECTED.value

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout_seconds
        current_interval = self.poll_interval_seconds
        max_interval = 60

        while loop.time() < deadline:
            status = await self.check_status(task_id=task_id, issue_key=issue_key, since=requested_at)
            if status in {ApprovalStatus.APPROVED.value, ApprovalStatus.REJECTED.value}:
                await self.state_manager.update_state(
                    task_id,
                    "IN_PROGRESS" if status == ApprovalStatus.APPROVED.value else "FAILED",
                    metadata={
                        "sub_state": "APPROVAL_GRANTED"
                        if status == ApprovalStatus.APPROVED.value
                        else "APPROVAL_REJECTED",
                        "action": action_type,
                    },
                )
                return status
            await asyncio.sleep(current_interval)
            current_interval = min(current_interval * 1.5, max_interval)

        logger.warning("Approval timed out for task_id=%s issue=%s", task_id, issue_key)
        return ApprovalStatus.TIMEOUT.value

    async def check_status(
        self,
        task_id: str,
        issue_key: str | None = None,
        since: datetime | None = None,
    ) -> str:
        target_issue = issue_key or task_id
        since = since or datetime.fromtimestamp(0, tz=UTC)
        try:
            comments = self.jira_client.list_comments(target_issue)
        except JiraClientError as exc:
            logger.warning("Failed to poll Jira comments for %s: %s", target_issue, exc)
            return ApprovalStatus.PENDING.value

        for comment in comments:
            created_raw = comment.get("created", "")
            try:
                created = datetime.strptime(created_raw, "%Y-%m-%dT%H:%M:%S.%f%z")
                created = created.astimezone(UTC)
            except Exception:
                continue
            if created < since:
                continue
            signal = self._is_approval_signal(self._comment_to_text(comment))
            if signal:
                return signal
        return ApprovalStatus.PENDING.value
