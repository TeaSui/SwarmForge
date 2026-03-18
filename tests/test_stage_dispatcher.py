"""Direct unit tests for StageDispatcher — covers the generic gate helper,
stage routing, and the async utility."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.executor.stage_dispatcher import StageDispatcher, StageExecutionError, run_coroutine_in_thread


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dispatcher(tmp_path: Path) -> StageDispatcher:
    git_ops = MagicMock()
    git_ops.run_command.return_value = {
        "command": "pytest",
        "returncode": 0,
        "stdout_tail": "ok",
        "stderr_tail": "",
    }
    git_ops.run_first_available.return_value = {
        "command": "pytest",
        "returncode": 0,
        "stdout_tail": "ok",
        "stderr_tail": "",
    }
    delivery = MagicMock()
    delivery.create_pr_for_jira_issue.return_value = {"enabled": False, "reason": "test"}
    return StageDispatcher(
        workspace_root=tmp_path,
        git_ops=git_ops,
        delivery=delivery,
    )


@pytest.fixture
def failing_dispatcher(tmp_path: Path) -> StageDispatcher:
    git_ops = MagicMock()
    git_ops.run_command.return_value = {
        "command": "pytest",
        "returncode": 1,
        "stdout_tail": "",
        "stderr_tail": "FAILED",
    }
    delivery = MagicMock()
    delivery.create_pr_for_jira_issue.return_value = {"enabled": False}
    return StageDispatcher(
        workspace_root=tmp_path,
        git_ops=git_ops,
        delivery=delivery,
    )


# ---------------------------------------------------------------------------
# _run_command_gate
# ---------------------------------------------------------------------------

class TestRunCommandGate:
    def test_passing_gate_sets_artifact(self, dispatcher: StageDispatcher, tmp_path: Path):
        result: dict = {}
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        dispatcher._run_command_gate(
            command=["pytest"],
            run_dir=run_dir,
            artifact_name="TEST.json",
            failure_label="Tests failed",
            result=result,
        )
        assert result["artifact"] == "TEST.json"
        assert "warning" not in result
        assert (run_dir / "TEST.json").exists()
        data = json.loads((run_dir / "TEST.json").read_text())
        assert data["returncode"] == 0

    def test_failing_gate_sets_warning(self, failing_dispatcher: StageDispatcher, tmp_path: Path):
        result: dict = {}
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        failing_dispatcher._run_command_gate(
            command=["pytest"],
            run_dir=run_dir,
            artifact_name="TEST.json",
            failure_label="Tests failed",
            result=result,
        )
        assert "warning" in result
        assert "Tests failed" in result["warning"]

    def test_strict_mode_raises(self, failing_dispatcher: StageDispatcher, tmp_path: Path):
        failing_dispatcher._strict = True
        result: dict = {}
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        with pytest.raises(StageExecutionError, match="Tests failed"):
            failing_dispatcher._run_command_gate(
                command=["pytest"],
                run_dir=run_dir,
                artifact_name="TEST.json",
                failure_label="Tests failed",
                result=result,
            )


# ---------------------------------------------------------------------------
# execute_stage routing
# ---------------------------------------------------------------------------

class TestExecuteStageRouting:
    @pytest.mark.parametrize("stage,expected_artifact", [
        ("intent-analysis", "intent.json"),
        ("solution-plan", "PLAN.md"),
        ("documentation", "REPORT.md"),
        ("test-verification", "TEST.json"),
        ("e2e-verification", "E2E.json"),
        ("ui-accessibility-gate", "UI_A11Y.json"),
        ("post-deploy-slo-gate", "SLO_GATE.json"),
        ("release-gate", "RELEASE_GATE.json"),
    ])
    def test_stage_produces_expected_artifact(self, dispatcher: StageDispatcher, stage: str, expected_artifact: str):
        with patch.object(dispatcher, "task_run_dir") as mock_dir:
            run_dir = dispatcher.workspace_root / "test_run"
            run_dir.mkdir(parents=True, exist_ok=True)
            mock_dir.return_value = run_dir

            context = {"summary": "Test task", "labels": ["ai-task"], "source": "jira"}
            result = dispatcher.execute_stage("TST-1", stage, context)
            assert result["artifact"] == expected_artifact

    def test_unknown_stage_returns_none_artifact(self, dispatcher: StageDispatcher):
        with patch.object(dispatcher, "task_run_dir") as mock_dir:
            run_dir = dispatcher.workspace_root / "test_run"
            run_dir.mkdir(parents=True, exist_ok=True)
            mock_dir.return_value = run_dir

            result = dispatcher.execute_stage("TST-1", "nonexistent-stage", {})
            assert result["artifact"] is None


# ---------------------------------------------------------------------------
# run_coroutine_in_thread
# ---------------------------------------------------------------------------

class TestRunCoroutineInThread:
    def test_runs_simple_coroutine(self):
        async def add(a: int, b: int) -> int:
            return a + b

        assert run_coroutine_in_thread(add(2, 3)) == 5

    def test_propagates_exceptions(self):
        async def boom():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            run_coroutine_in_thread(boom())
