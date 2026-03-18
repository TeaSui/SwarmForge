"""Tests for the TaskNotifications service."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.task_notifications import TaskNotifications


@pytest.fixture
def mock_jira():
    with patch("services.task_notifications.JiraClient") as cls:
        client = MagicMock()
        cls.from_settings.return_value = client
        yield client


class TestTaskNotifications:
    def test_disabled_when_no_issue_key(self, mock_jira):
        notifier = TaskNotifications(jira_issue_key=None)
        assert notifier.enabled is False

    def test_enabled_with_issue_key(self, mock_jira):
        notifier = TaskNotifications(jira_issue_key="TST-1")
        assert notifier.enabled is True

    def test_post_skipped_when_disabled(self, mock_jira):
        notifier = TaskNotifications(jira_issue_key=None)
        notifier.notify_plan_created(5)
        mock_jira.add_comment.assert_not_called()

    def test_notify_plan_created_posts_stage_count(self, mock_jira):
        notifier = TaskNotifications(jira_issue_key="TST-1")
        notifier.notify_plan_created(7)

        mock_jira.add_comment.assert_called_once()
        issue_key, text = mock_jira.add_comment.call_args.args
        assert issue_key == "TST-1"
        assert "7 stages" in text

    def test_notify_completion_includes_pr_url(self, mock_jira):
        notifier = TaskNotifications(jira_issue_key="TST-1")
        notifier.notify_completion(pr_url="https://github.com/a/b/pull/42")

        text = mock_jira.add_comment.call_args.args[1]
        assert "PR: https://github.com/a/b/pull/42" in text

    @pytest.mark.parametrize("method,args,expected_fragment", [
        ("notify_stage_timeout", ("code-gen",), "code-gen timed out"),
        ("notify_approval_rejected", (), "rejected"),
        ("notify_approval_timeout", (), "timed out"),
        ("notify_approval_waiting", (), "Waiting for human approval"),
        ("notify_quality_gates_failed", (["tests-pass", "security"],), "tests-pass, security"),
        ("notify_budget_exceeded", (RuntimeError("over budget"),), "over budget"),
        ("notify_execution_failed", (RuntimeError("boom"),), "boom"),
    ])
    def test_notification_messages(self, mock_jira, method: str, args: tuple, expected_fragment: str):
        notifier = TaskNotifications(jira_issue_key="TST-1")
        getattr(notifier, method)(*args)

        text = mock_jira.add_comment.call_args.args[1]
        assert expected_fragment in text

    def test_jira_error_logged_not_raised(self, mock_jira):
        from services.jira_client import JiraClientError
        mock_jira.add_comment.side_effect = JiraClientError("connection refused")

        notifier = TaskNotifications(jira_issue_key="TST-1")
        notifier.notify_plan_created(3)  # should not raise
