"""Centralized notification service for SwarmForge task lifecycle events.

Decouples notification logic (Jira comments, future Slack/email) from the
orchestrator so that adding new notification channels requires zero changes
to the orchestration pipeline.
"""
from __future__ import annotations

import logging
from typing import Any

from config import settings
from services.jira_client import JiraClient, JiraClientError

logger = logging.getLogger(__name__)


class TaskNotifications:
    """Posts structured updates to external systems (currently Jira)."""

    PREFIX = "[SwarmForge]"

    def __init__(self, jira_issue_key: str | None = None):
        self._issue_key = jira_issue_key
        self._jira = JiraClient.from_settings()

    @property
    def enabled(self) -> bool:
        return self._issue_key is not None

    # ------------------------------------------------------------------
    # Lifecycle events
    # ------------------------------------------------------------------

    def notify_plan_created(self, stage_count: int) -> None:
        self._post(f"{self.PREFIX} Planned autonomous execution with {stage_count} stages.")

    def notify_stage_timeout(self, stage_name: str) -> None:
        self._post(f"{self.PREFIX} Stage {stage_name} timed out.")

    def notify_approval_rejected(self) -> None:
        self._post(f"{self.PREFIX} Human approval rejected the critical action.")

    def notify_approval_timeout(self) -> None:
        self._post(f"{self.PREFIX} Approval timed out for critical action.")

    def notify_approval_waiting(self) -> None:
        self._post(f"{self.PREFIX} Waiting for human approval before critical release action.")

    def notify_quality_gates_failed(self, failed_checks: list[str]) -> None:
        joined = ", ".join(failed_checks)
        self._post(f"{self.PREFIX} Quality gates failed. Failed checks: {joined}")

    def notify_budget_exceeded(self, error: Exception) -> None:
        self._post(f"{self.PREFIX} Budget guardrail triggered: {error}")

    def notify_execution_failed(self, error: Exception) -> None:
        self._post(f"{self.PREFIX} Execution failed: {error}")

    def notify_completion(
        self,
        *,
        pr_url: str | None = None,
        quality_report: dict[str, Any] | None = None,
    ) -> None:
        msg = f"{self.PREFIX} Autonomous execution completed successfully."
        if pr_url:
            msg = f"{self.PREFIX} Autonomous execution completed successfully. PR: {pr_url}"
        if quality_report and quality_report.get("enabled"):
            total = len(quality_report.get("checks", []))
            msg += f" Quality gates: passed ({total}/{total})."
        self._post(msg)

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _post(self, message: str) -> None:
        if not self.enabled:
            return
        try:
            self._jira.add_comment(self._issue_key, message)
        except JiraClientError as exc:
            logger.warning("Jira notification failed for %s: %s", self._issue_key, exc)
