import logging
import time
from typing import Any

import requests
from config import settings

logger = logging.getLogger(__name__)

_RETRY_BACKOFF_SECONDS = [1, 2, 4]


class NotificationService:
    """Service to handle multi-channel notifications for approvals and alerts."""

    def __init__(self) -> None:
        self.slack_url = settings.SLACK_WEBHOOK_URL

    async def notify_approval_requested(self, task_id: str, details: dict[str, Any]) -> None:
        """Sends a notification to Slack for manual approval."""
        if not self.slack_url:
            logger.warning("Slack webhook URL not configured, skipping notification for %s", task_id)
            return

        payload = {
            "text": (
                f"*Human Approval Required*\n"
                f"*Task ID:* `{task_id}`\n"
                f"*Action:* {details.get('action')}\n"
                f"*Context:* {details.get('details')}"
            ),
            "attachments": [
                {
                    "fallback": "Approve or Reject via Jira/Slack",
                    "actions": [
                        {
                            "type": "button",
                            "text": "View in Jira",
                            "url": f"{settings.JIRA_BASE_URL}/browse/{task_id}",
                        }
                    ],
                }
            ],
        }

        max_attempts = settings.NOTIFICATION_MAX_ATTEMPTS
        for attempt in range(max_attempts):
            try:
                response = requests.post(self.slack_url, json=payload, timeout=10)
                if response.status_code == 200:
                    logger.info("Sent Slack notification for task %s", task_id)
                    return
                logger.error("Failed to send Slack notification (status=%d)", response.status_code)
            except requests.RequestException as exc:
                logger.error("NotificationService error on attempt %d: %s", attempt + 1, exc)
            if attempt < max_attempts - 1 and attempt < len(_RETRY_BACKOFF_SECONDS):
                time.sleep(_RETRY_BACKOFF_SECONDS[attempt])

        logger.error("All notification attempts failed for task %s", task_id)


notification_service = NotificationService()
