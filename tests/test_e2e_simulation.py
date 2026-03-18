import pytest
from unittest.mock import AsyncMock, patch

from services.approval_gate import ApprovalStatus
from services.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_orchestrator_release_flow_waits_for_approval():
    orchestrator = Orchestrator()
    task_id = "SCRUM-RELEASE-1"
    envelope = {
        "source": "jira",
        "task_id": task_id,
        "payload": {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": task_id,
                "fields": {
                    "summary": "Production release for health app",
                    "labels": ["ai-task", "production"],
                },
            },
        },
    }

    with patch("services.orchestrator.StateManager.update_state", new_callable=AsyncMock) as mock_update, \
         patch("services.budget_manager.BudgetManager.persist_usage", new_callable=AsyncMock), \
         patch("services.budget_manager.BudgetManager.add_usage", new_callable=AsyncMock), \
         patch("services.budget_manager.BudgetManager.reset", new_callable=AsyncMock), \
         patch("services.orchestrator.CrewStageRunner.run", return_value={"mode": "adapter", "agents": [], "output": ""}), \
         patch("services.autonomous_executor.AutonomousExecutor.execute_stage", return_value={"artifact": "ok"}), \
         patch("services.approval_gate.ApprovalGate.request_approval", new_callable=AsyncMock) as mock_approval:
        mock_approval.return_value = ApprovalStatus.TIMEOUT.value
        await orchestrator.handle_task(envelope)

        states = [call.args[1] for call in mock_update.call_args_list]
        assert "FAILED" in states
        assert states[-1] == "FAILED"
