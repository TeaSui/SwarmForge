from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from services.approval_gate import ApprovalGate, ApprovalStatus
from services.jira_client import JiraClientError


class _StubJiraClient:
    def __init__(self, comments=None, fail_add=False):
        self._comments = comments or []
        self._fail_add = fail_add

    def add_comment(self, issue_key: str, text: str):
        if self._fail_add:
            raise JiraClientError("add comment failed")
        return {"id": "1", "issue_key": issue_key, "text": text}

    def list_comments(self, issue_key: str):
        return self._comments


@pytest.mark.asyncio
async def test_check_status_returns_approved_from_jira_comment():
    created = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    jira = _StubJiraClient(
        comments=[
            {
                "created": created,
                "body": {
                    "content": [
                        {"content": [{"text": "looks good /approve now"}]},
                    ]
                },
            }
        ]
    )
    with patch("services.approval_gate.JiraClient.from_settings", return_value=jira):
        gate = ApprovalGate(state_manager=AsyncMock())
        status = await gate.check_status(task_id="SCRUM-1", issue_key="SCRUM-1", since=datetime(1970, 1, 1, tzinfo=UTC))
    assert status == ApprovalStatus.APPROVED.value


@pytest.mark.asyncio
async def test_request_approval_returns_rejected_when_jira_comment_fails():
    jira = _StubJiraClient(fail_add=True)
    state_manager = AsyncMock()
    with patch("services.approval_gate.JiraClient.from_settings", return_value=jira):
        gate = ApprovalGate(state_manager=state_manager)
        status = await gate.request_approval(
            task_id="SCRUM-2",
            action_type="release-gate",
            details={"jira_issue_key": "SCRUM-2"},
        )
    assert status == ApprovalStatus.REJECTED.value


@pytest.mark.asyncio
async def test_request_approval_returns_approved_when_signal_found():
    jira = _StubJiraClient()
    state_manager = AsyncMock()
    with patch("services.approval_gate.JiraClient.from_settings", return_value=jira):
        gate = ApprovalGate(state_manager=state_manager)
        gate.timeout_seconds = 30
        gate.poll_interval_seconds = 2
        gate.check_status = AsyncMock(return_value=ApprovalStatus.APPROVED.value)
        status = await gate.request_approval(
            task_id="SCRUM-3",
            action_type="release-gate",
            details={"jira_issue_key": "SCRUM-3"},
        )
    assert status == ApprovalStatus.APPROVED.value
