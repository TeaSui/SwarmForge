from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from config import settings
from services.approval_gate import ApprovalGate, ApprovalStatus
from services.agents import get_stage_extensions
from services.autonomous_executor import AutonomousExecutor, StageExecutionError
from services.aws_session import get_boto3_session
from services.budget_manager import BudgetExceededError, budget_manager
from services.crew_stage_runner import CrewStageRunner
from services.quality_gate import QualityGateEvaluator
from services.task_notifications import TaskNotifications
from services.logging_setup import clear_correlation_id, set_correlation_id

logger = logging.getLogger(__name__)

_ROLLOUT_RE = re.compile(r"\b(?:deploy|release|prod|go-live)\b")
_E2E_RE = re.compile(r"\b(?:e2e|uat|regression|smoke|production-readiness)\b")
_UI_RE = re.compile(r"\b(?:ui|frontend|design|theme|ux|a11y|accessibility)\b")


@dataclass
class SwarmStage:
    name: str
    token_estimate: int
    usd_estimate: float
    critical: bool = False
    timeout_seconds: int = 300


@dataclass
class TaskContext:
    task_id: str
    source: str
    event_type: str
    summary: str
    labels: list[str]
    payload: dict[str, Any]


class StateManager:
    def __init__(self):
        session = get_boto3_session()
        endpoint_url = settings.AWS_ENDPOINT_URL
        kwargs = {"region_name": settings.AWS_REGION}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self.dynamodb = session.resource("dynamodb", **kwargs)
        self.table_name = "swarmforge-tasks"
        self.table = self.dynamodb.Table(self.table_name)

    def _sanitize_for_dynamodb(self, value: Any) -> Any:
        if isinstance(value, float):
            return f"{value:.6f}"
        if isinstance(value, dict):
            return {k: self._sanitize_for_dynamodb(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._sanitize_for_dynamodb(v) for v in value]
        return value

    async def update_state(
        self,
        task_id: str,
        state: str,
        metadata: Dict[str, Any] | None = None,
    ):
        metadata = metadata or {}
        logger.info("Task %s -> %s", task_id, state)
        try:
            now = datetime.now(UTC).isoformat()
            safe_metadata = self._sanitize_for_dynamodb(metadata)
            self.table.update_item(
                Key={"task_id": task_id},
                UpdateExpression=(
                    "SET #state = :state, updated_at = :updated_at, "
                    "metadata = :metadata"
                ),
                ExpressionAttributeNames={"#state": "state"},
                ExpressionAttributeValues={
                    ":state": state,
                    ":updated_at": now,
                    ":metadata": safe_metadata,
                },
            )
        except ClientError as exc:
            logger.warning(
                "Failed to persist state for %s (%s): %s",
                task_id,
                self.table_name,
                exc,
            )
        except Exception as exc:
            logger.warning("Unexpected state persistence error for %s: %s", task_id, exc)


class Orchestrator:
    def __init__(self):
        self.state_manager = StateManager()
        self.approval_gate = ApprovalGate(self.state_manager)
        self.executor = AutonomousExecutor()
        self.crew_runner = CrewStageRunner()
        self.quality_gate = QualityGateEvaluator()

    # ------------------------------------------------------------------
    # Context parsing
    # ------------------------------------------------------------------

    def _extract_task_context(self, envelope: dict) -> TaskContext:
        source = envelope.get("source", "unknown")
        payload = envelope.get("payload", envelope)
        task_id = envelope.get("task_id")
        event_type = envelope.get("event_type", "unknown")

        if source == "jira" or "issue" in payload:
            issue = payload.get("issue", {})
            fields = issue.get("fields", {})
            return TaskContext(
                task_id=task_id or issue.get("key") or issue.get("id") or "unknown",
                source="jira",
                event_type=payload.get("webhookEvent", event_type),
                summary=fields.get("summary", ""),
                labels=fields.get("labels", []),
                payload=payload,
            )

        if source == "slack" or "event" in payload:
            event = payload.get("event", {})
            return TaskContext(
                task_id=task_id or payload.get("event_id") or event.get("ts") or "unknown",
                source="slack",
                event_type=event_type,
                summary=event.get("text", ""),
                labels=[],
                payload=payload,
            )

        return TaskContext(
            task_id=task_id or payload.get("id", "unknown"),
            source=source,
            event_type=event_type,
            summary="",
            labels=[],
            payload=payload,
        )

    # ------------------------------------------------------------------
    # Plan building
    # ------------------------------------------------------------------

    def _build_plan(self, ctx: TaskContext) -> List[SwarmStage]:
        summary = (ctx.summary or "").lower()
        labels = {str(x).lower() for x in ctx.labels}
        ui_labels = {"ui", "frontend"}
        release_labels = {"release", "prod-release", "deploy"}

        summary_has_release_keyword = bool(_ROLLOUT_RE.search(summary))
        is_release_flow = bool(release_labels.intersection(labels)) or summary_has_release_keyword
        has_e2e_signal = bool({"e2e", "uat", "regression", "smoke", "production-readiness"}.intersection(labels)) or bool(_E2E_RE.search(summary))
        is_ui_flow = bool(ui_labels.intersection(labels)) or bool(_UI_RE.search(summary))

        stages: List[SwarmStage] = [
            SwarmStage("intent-analysis", 400, 0.006),
            SwarmStage("solution-plan", 800, 0.012),
            SwarmStage("code-generation", 2500, 0.038),
            SwarmStage("code-review", 1200, 0.018),
            SwarmStage("test-verification", 1500, 0.022),
            SwarmStage("security-check", 900, 0.014),
        ]
        if is_release_flow or has_e2e_signal:
            stages.append(SwarmStage("e2e-verification", 1700, 0.026))
        if is_ui_flow:
            stages.append(SwarmStage("ui-accessibility-gate", 900, 0.014))
        stages.append(SwarmStage("documentation", 600, 0.009))
        if is_release_flow:
            stages.extend(
                [
                    SwarmStage("post-deploy-slo-gate", 1000, 0.015),
                    SwarmStage("release-gate", 300, 0.005, critical=True, timeout_seconds=900),
                ]
            )
        return stages

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ctx_as_dict(self, ctx: TaskContext) -> dict[str, Any]:
        return {
            "task_id": ctx.task_id,
            "source": ctx.source,
            "event_type": ctx.event_type,
            "summary": ctx.summary,
            "labels": ctx.labels,
            "payload": ctx.payload,
        }

    def _jira_issue_key(self, ctx: TaskContext) -> str | None:
        if ctx.source != "jira":
            return None
        issue = ctx.payload.get("issue", {})
        return issue.get("key")

    def _extract_delivery_workspace(self, stage_results: dict[str, dict[str, Any]]) -> str | None:
        """Extract the delivery repo workspace path from codegen stage results."""
        codegen = stage_results.get("code-generation", {})
        delivery = codegen.get("delivery", {})
        if isinstance(delivery, dict):
            run_dir = codegen.get("run_dir")
            if run_dir:
                from pathlib import Path
                delivery_repo = Path(run_dir) / "delivery_repo"
                if delivery_repo.is_dir():
                    return str(delivery_repo)
        return None

    def _is_crew_fallback(self, crew_result: dict[str, Any]) -> bool:
        """Detect if CrewAI fell back to adapter mode instead of real execution."""
        mode = crew_result.get("mode", "")
        if mode == "adapter":
            return True
        if mode == "none":
            return True
        output = str(crew_result.get("output", ""))
        if "fallback execution:" in output:
            return True
        return False

    # ------------------------------------------------------------------
    # Stage execution
    # ------------------------------------------------------------------

    async def _run_swarm_stage(
        self,
        task_id: str,
        stage: SwarmStage,
        ctx: TaskContext,
        prior_results: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        await budget_manager.add_usage(stage.token_estimate, stage.usd_estimate)
        context_dict = self._ctx_as_dict(ctx)

        # Inject delivery workspace from codegen for downstream stages.
        delivery_workspace = self._extract_delivery_workspace(prior_results)
        if delivery_workspace:
            context_dict["_delivery_workspace"] = delivery_workspace

        # Inject prior stage results for stages that need them.
        context_dict["_prior_results"] = prior_results

        crew_result = self.crew_runner.run(stage.name, context_dict)
        stage_result = self.executor.execute_stage(task_id, stage.name, context_dict)
        stage_result["crew"] = crew_result

        if self._is_crew_fallback(crew_result):
            stage_result["crew_fallback"] = True
            logger.warning(
                "Stage %s used CrewAI fallback mode (adapter) for task %s",
                stage.name, task_id,
            )

        await self.state_manager.update_state(
            task_id,
            "IN_PROGRESS",
            metadata={
                "sub_state": "STAGE_COMPLETED",
                "stage": stage.name,
                "tokens": budget_manager.current_tokens,
                "usd": round(budget_manager.current_usd, 6),
                "result": stage_result,
            },
        )
        return stage_result

    async def _execute_stages(
        self,
        ctx: TaskContext,
        plan: List[SwarmStage],
        notifier: TaskNotifications,
    ) -> tuple[dict[str, dict[str, Any]], str | None]:
        """Execute all stages in *plan*, returning stage results and optional PR URL."""
        pr_url: str | None = None
        stage_results: dict[str, dict[str, Any]] = {}

        for stage in plan:
            stage_extensions = get_stage_extensions(stage.name)
            await self.state_manager.update_state(
                ctx.task_id,
                "IN_PROGRESS",
                metadata={
                    "sub_state": "STAGE_RUNNING",
                    "stage": stage.name,
                    "extensions": stage_extensions,
                },
            )

            try:
                stage_result = await asyncio.wait_for(
                    self._run_swarm_stage(ctx.task_id, stage, ctx, stage_results),
                    timeout=stage.timeout_seconds,
                )
            except asyncio.TimeoutError:
                await self.state_manager.update_state(
                    ctx.task_id,
                    "FAILED",
                    metadata={"sub_state": "STAGE_TIMEOUT", "stage": stage.name},
                )
                notifier.notify_stage_timeout(stage.name)
                return stage_results, pr_url

            stage_results[stage.name] = stage_result
            delivery = stage_result.get("delivery", {})
            if isinstance(delivery, dict) and delivery.get("pr_url"):
                pr_url = delivery["pr_url"]

            if stage.critical:
                should_stop = await self._handle_approval(ctx, stage, notifier)
                if should_stop:
                    return stage_results, pr_url

        return stage_results, pr_url

    async def _handle_approval(
        self,
        ctx: TaskContext,
        stage: SwarmStage,
        notifier: TaskNotifications,
    ) -> bool:
        """Request human approval for a critical stage. Returns True if pipeline should stop."""
        approval = await self.approval_gate.request_approval(
            ctx.task_id,
            action_type=stage.name,
            details={
                "jira_issue_key": self._jira_issue_key(ctx),
                "summary": ctx.summary,
                "estimated_cost_usd": round(budget_manager.current_usd, 4),
            },
        )

        if approval == ApprovalStatus.REJECTED.value:
            await self.state_manager.update_state(
                ctx.task_id, "FAILED",
                metadata={"sub_state": "APPROVAL_REJECTED", "stage": stage.name},
            )
            notifier.notify_approval_rejected()
            return True

        if approval == ApprovalStatus.TIMEOUT.value:
            await self.state_manager.update_state(
                ctx.task_id, "FAILED",
                metadata={"sub_state": "APPROVAL_TIMEOUT", "stage": stage.name},
            )
            notifier.notify_approval_timeout()
            return True

        if approval != ApprovalStatus.APPROVED.value:
            await self.state_manager.update_state(
                ctx.task_id, "APPROVAL_NEEDED",
                metadata={"stage": stage.name},
            )
            notifier.notify_approval_waiting()
            return True

        return False

    async def _evaluate_quality(
        self,
        ctx: TaskContext,
        stage_results: dict[str, dict[str, Any]],
        pr_url: str | None,
        notifier: TaskNotifications,
    ) -> bool:
        """Run quality gates and update state. Returns True when all gates pass."""
        quality_report = self.quality_gate.evaluate(
            context=self._ctx_as_dict(ctx),
            stage_results=stage_results,
            pr_url=pr_url,
        )

        if not quality_report.get("passed", False):
            failed_checks = quality_report.get("failed_checks", [])
            logger.warning(
                "Quality gates FAILED for task %s: %s",
                ctx.task_id, failed_checks,
            )
            await self.state_manager.update_state(
                ctx.task_id, "FAILED",
                metadata={
                    "sub_state": "QUALITY_GATES_FAILED",
                    "failed_checks": failed_checks,
                    "quality_report": quality_report,
                },
            )
            notifier.notify_quality_gates_failed(quality_report.get("failed_checks", []))
            return False

        await budget_manager.persist_usage(ctx.task_id)
        await self.state_manager.update_state(
            ctx.task_id, "COMPLETED",
            metadata={
                "sub_state": "COMPLETED",
                "tokens": budget_manager.current_tokens,
                "usd": round(budget_manager.current_usd, 6),
                "quality_report": quality_report,
            },
        )
        notifier.notify_completion(pr_url=pr_url, quality_report=quality_report)
        return True

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def handle_task(self, envelope: dict):
        ctx = self._extract_task_context(envelope)
        task_id = ctx.task_id
        set_correlation_id(task_id)
        jira_issue_key = self._jira_issue_key(ctx)
        notifier = TaskNotifications(jira_issue_key)
        await budget_manager.reset()

        await self.state_manager.update_state(
            task_id, "PENDING",
            metadata={
                "sub_state": "PROCESSING",
                "source": ctx.source,
                "event_type": ctx.event_type,
                "summary": ctx.summary,
            },
        )

        try:
            plan = self._build_plan(ctx)
            await self.state_manager.update_state(
                task_id, "INTENT_PARSED",
                metadata={"stages": [s.name for s in plan]},
            )
            notifier.notify_plan_created(len(plan))

            stage_results, pr_url = await self._execute_stages(ctx, plan, notifier)
            if not stage_results or task_id != ctx.task_id:
                # Pipeline was halted early (timeout / approval).
                return

            await self._evaluate_quality(ctx, stage_results, pr_url, notifier)

        except BudgetExceededError as exc:
            await self.state_manager.update_state(task_id, "FAILED", metadata={"error": str(exc)})
            notifier.notify_budget_exceeded(exc)
        except Exception as exc:
            await self.state_manager.update_state(task_id, "FAILED", metadata={"error": str(exc)})
            notifier.notify_execution_failed(exc)
            logger.exception("Orchestrator failed for task %s", task_id)
        finally:
            clear_correlation_id()


orchestrator = Orchestrator()
