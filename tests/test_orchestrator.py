import pytest
from unittest.mock import patch, AsyncMock
from services.orchestrator import orchestrator, TaskContext
from services.task_notifications import TaskNotifications

@pytest.mark.asyncio
async def test_orchestrator_handle_task_lifecycle():
    envelope = {
        "task_id": "test-task-123",
        "source": "jira",
        "payload": {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "test-task-123",
                "fields": {"summary": "Fix something", "labels": ["ai-task"]},
            },
        },
    }

    with patch("services.orchestrator.StateManager.update_state", new_callable=AsyncMock) as mock_update, \
         patch("services.budget_manager.BudgetManager.persist_usage", new_callable=AsyncMock), \
         patch("services.budget_manager.BudgetManager.add_usage", new_callable=AsyncMock), \
         patch("services.budget_manager.BudgetManager.reset", new_callable=AsyncMock), \
         patch("services.orchestrator.CrewStageRunner.run", return_value={"mode": "adapter", "agents": [], "output": ""}) as mock_crew_run, \
         patch("services.autonomous_executor.AutonomousExecutor.execute_stage", return_value={"artifact": "ok"}), \
         patch(
             "services.orchestrator.QualityGateEvaluator.evaluate",
             return_value={"enabled": True, "passed": True, "checks": []},
         ):
        await orchestrator.handle_task(envelope)

        states = [call.args[1] for call in mock_update.call_args_list]
        assert "PENDING" in states
        assert "INTENT_PARSED" in states
        assert "IN_PROGRESS" in states
        assert states[-1] == "COMPLETED"
        assert mock_crew_run.called


@pytest.mark.asyncio
async def test_orchestrator_blocks_when_quality_gates_fail():
    envelope = {
        "task_id": "test-task-quality-fail",
        "source": "jira",
        "payload": {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "test-task-quality-fail",
                "fields": {"summary": "Fix dashboard UI", "labels": ["session-dashboard"]},
            },
        },
    }

    with patch("services.orchestrator.StateManager.update_state", new_callable=AsyncMock) as mock_update, \
         patch("services.budget_manager.BudgetManager.persist_usage", new_callable=AsyncMock), \
         patch("services.budget_manager.BudgetManager.add_usage", new_callable=AsyncMock), \
         patch("services.budget_manager.BudgetManager.reset", new_callable=AsyncMock), \
         patch("services.orchestrator.CrewStageRunner.run", return_value={"mode": "adapter", "agents": [], "output": ""}), \
         patch("services.autonomous_executor.AutonomousExecutor.execute_stage", return_value={"artifact": "ok"}), \
         patch(
             "services.orchestrator.QualityGateEvaluator.evaluate",
             return_value={"enabled": True, "passed": False, "failed_checks": ["ui-design-signal"], "checks": []},
         ):
        await orchestrator.handle_task(envelope)

        states = [call.args[1] for call in mock_update.call_args_list]
        assert "FAILED" in states
        assert states[-1] == "FAILED"


def test_build_plan_includes_release_e2e_and_slo_stages():
    plan = orchestrator._build_plan(
        TaskContext(task_id="t", source="jira", event_type="e",
                    summary="Prepare prod release and production-readiness",
                    labels=["release"], payload={})
    )
    names = [s.name for s in plan]
    assert "e2e-verification" in names
    assert "post-deploy-slo-gate" in names
    assert "release-gate" in names


def test_build_plan_includes_ui_accessibility_stage():
    plan = orchestrator._build_plan(
        TaskContext(task_id="t", source="jira", event_type="e",
                    summary="Improve UI accessibility and theme",
                    labels=["session-dashboard"], payload={})
    )
    names = [s.name for s in plan]
    assert "ui-accessibility-gate" in names


def test_build_plan_session_dashboard_label_alone_is_not_ui_scope():
    plan = orchestrator._build_plan(
        TaskContext(task_id="t", source="jira", event_type="e",
                    summary="Backend ingestion reliability",
                    labels=["session-dashboard"], payload={})
    )
    names = [s.name for s in plan]
    assert "ui-accessibility-gate" not in names


# ---------------------------------------------------------------------------
# Parametrized plan building
# ---------------------------------------------------------------------------

class TestBuildPlanParametrized:
    @pytest.mark.parametrize("summary,labels,expected_stages,excluded_stages", [
        (
            "Fix login bug",
            ["ai-task"],
            ["intent-analysis", "code-generation", "documentation"],
            ["e2e-verification", "ui-accessibility-gate", "release-gate"],
        ),
        (
            "Deploy to production",
            ["release"],
            ["e2e-verification", "post-deploy-slo-gate", "release-gate"],
            ["ui-accessibility-gate"],
        ),
        (
            "Improve UI theme and design",
            ["frontend"],
            ["ui-accessibility-gate"],
            ["release-gate", "post-deploy-slo-gate"],
        ),
        (
            "E2E regression suite",
            ["e2e"],
            ["e2e-verification"],
            ["release-gate", "ui-accessibility-gate"],
        ),
        (
            "Full release with UI",
            ["release", "ui"],
            ["e2e-verification", "ui-accessibility-gate", "release-gate", "post-deploy-slo-gate"],
            [],
        ),
    ])
    def test_plan_stages(
        self,
        summary: str,
        labels: list[str],
        expected_stages: list[str],
        excluded_stages: list[str],
    ):
        ctx = TaskContext(
            task_id="t", source="jira", event_type="e",
            summary=summary, labels=labels, payload={},
        )
        plan = orchestrator._build_plan(ctx)
        names = [s.name for s in plan]
        for stage in expected_stages:
            assert stage in names, f"Expected {stage} in plan for '{summary}' {labels}"
        for stage in excluded_stages:
            assert stage not in names, f"Did not expect {stage} in plan for '{summary}' {labels}"
