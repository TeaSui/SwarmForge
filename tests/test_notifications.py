import pytest
from unittest.mock import patch, MagicMock
from services.notifications import NotificationService


@pytest.mark.asyncio
async def test_notify_skipped_when_no_slack_url():
    service = NotificationService()
    service.slack_url = None
    # Should not raise, just log a warning
    await service.notify_approval_requested("task-1", {"action": "release"})


@pytest.mark.asyncio
async def test_notify_sends_to_slack():
    service = NotificationService()
    service.slack_url = "https://hooks.slack.com/test"

    with patch("services.notifications.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        await service.notify_approval_requested(
            "task-2",
            {"action": "release-gate", "details": "production deploy"},
        )

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "task-2" in str(call_kwargs)


@pytest.mark.asyncio
async def test_notify_retries_on_failure():
    service = NotificationService()
    service.slack_url = "https://hooks.slack.com/test"

    with patch("services.notifications.requests.post") as mock_post, \
         patch("services.notifications.time.sleep"):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        await service.notify_approval_requested("task-3", {"action": "test"})

        assert mock_post.call_count == 3  # NOTIFICATION_MAX_ATTEMPTS
