from pathlib import Path
from unittest.mock import patch

import pytest

from services.autonomous_executor import AutonomousExecutor, StageExecutionError


def test_executor_creates_plan_artifact(tmp_path: Path):
    executor = AutonomousExecutor(workspace_root=str(tmp_path))
    result = executor.execute_stage(
        "TASK-1",
        "solution-plan",
        {"summary": "Build API", "labels": ["ai-task"], "source": "jira"},
    )
    plan_file = Path(result["run_dir"]) / "PLAN.md"
    assert plan_file.exists()
    assert "Build API" in plan_file.read_text(encoding="utf-8")


def test_executor_raises_when_test_stage_fails(tmp_path: Path):
    with patch.dict("os.environ", {"SWARMFORGE_STRICT_STAGE_FAILURES": "true"}):
        executor = AutonomousExecutor(workspace_root=str(tmp_path))
        with patch.object(
            executor._dispatcher.git_ops,
            "run_command",
            return_value={
                "command": "python -m pytest -q",
                "returncode": 1,
                "stdout_tail": "failed",
                "stderr_tail": "",
            },
        ):
            with pytest.raises(StageExecutionError):
                executor.execute_stage("TASK-2", "test-verification", {"summary": "", "labels": []})


def test_code_generation_attempts_delivery_when_enabled(tmp_path: Path):
    executor = AutonomousExecutor(workspace_root=str(tmp_path))
    context = {
        "source": "jira",
        "task_id": "SCRUM-999",
        "summary": "Real delivery",
        "payload": {"issue": {"key": "SCRUM-999"}},
    }

    with patch.dict(
        "os.environ",
        {
            "SWARMFORGE_GITHUB_DELIVERY_ENABLED": "true",
            "GITHUB_TOKEN": "test-token",
        },
    ), patch.object(
        executor._dispatcher.git_ops,
        "run_git",
        return_value={"command": "git", "returncode": 0, "stdout_tail": "", "stderr_tail": ""},
    ), patch("services.executor.github_delivery.requests.get") as mock_get, \
         patch("services.executor.github_delivery.requests.post") as mock_post:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            "html_url": "https://github.com/TeaSui/swarmforge-validation-flutter-health-app/pull/999",
            "number": 999,
        }
        result = executor.execute_stage("SCRUM-999", "code-generation", context)

    assert result["artifact"] == "CODEGEN.md"
    assert result["delivery"]["enabled"] is True
    assert result["delivery"]["pr_number"] == 999


def test_code_generation_reuses_existing_open_pr(tmp_path: Path):
    executor = AutonomousExecutor(workspace_root=str(tmp_path))
    context = {
        "source": "jira",
        "task_id": "SCRUM-1000",
        "summary": "Reuse open PR",
        "payload": {"issue": {"key": "SCRUM-1000"}},
    }

    with patch.dict(
        "os.environ",
        {
            "SWARMFORGE_GITHUB_DELIVERY_ENABLED": "true",
            "GITHUB_TOKEN": "test-token",
            "SWARMFORGE_TARGET_REPO": "TeaSui/swarmforge-session-dashboard",
        },
    ), patch("services.executor.github_delivery.requests.get") as mock_get, \
         patch("services.executor.github_delivery.requests.post") as mock_post:
        open_pr_response = {
            "status_code": 200,
            "json": lambda: [
                {
                    "title": "[SwarmForge] SCRUM-1000 Reuse open PR",
                    "html_url": "https://github.com/TeaSui/swarmforge-session-dashboard/pull/1000",
                    "number": 1000,
                    "head": {"ref": "codex/scrum-1000-abc"},
                    "base": {"ref": "main"},
                }
            ],
        }
        pr_files_response = {
            "status_code": 200,
            "json": lambda: [
                {"filename": "lib/main.dart"},
                {"filename": "test/dashboard_test.dart"},
            ],
        }

        class _FakeResp:
            def __init__(self, payload):
                self.status_code = payload["status_code"]
                self._json = payload["json"]

            def json(self):
                return self._json()

            def raise_for_status(self):
                if self.status_code >= 300:
                    raise RuntimeError("http error")

        mock_get.side_effect = [_FakeResp(open_pr_response), _FakeResp(pr_files_response)]
        result = executor.execute_stage("SCRUM-1000", "code-generation", context)

    assert result["delivery"]["enabled"] is True
    assert result["delivery"]["reused"] is True
    assert result["delivery"]["pr_number"] == 1000
    assert result["delivery"]["real_code_changed"] is True
    mock_post.assert_not_called()


def test_code_generation_does_not_reuse_open_pr_without_real_code(tmp_path: Path):
    executor = AutonomousExecutor(workspace_root=str(tmp_path))
    context = {
        "source": "jira",
        "task_id": "SCRUM-1001",
        "summary": "Create fresh PR if old one has only markers",
        "payload": {"issue": {"key": "SCRUM-1001"}},
    }

    with patch.dict(
        "os.environ",
        {
            "SWARMFORGE_GITHUB_DELIVERY_ENABLED": "true",
            "GITHUB_TOKEN": "test-token",
            "SWARMFORGE_TARGET_REPO": "TeaSui/swarmforge-session-dashboard",
        },
    ), patch.object(
        executor._dispatcher.git_ops,
        "run_git",
        return_value={"command": "git", "returncode": 0, "stdout_tail": "", "stderr_tail": ""},
    ), patch("services.executor.github_delivery.requests.get") as mock_get, \
         patch("services.executor.github_delivery.requests.post") as mock_post:
        open_prs = [
            {
                "title": "[SwarmForge] SCRUM-1001 Create fresh PR if old one has only markers",
                "html_url": "https://github.com/TeaSui/swarmforge-session-dashboard/pull/1001",
                "number": 1001,
                "head": {"ref": "codex/scrum-1000-abc"},
                "base": {"ref": "main"},
            }
        ]
        old_pr_files = [
            {"filename": "swarmforge_runs/SCRUM-1001.md"},
            {"filename": "lib/src/deliveries/scrum-1001_delivery.dart"},
        ]

        class _FakeResp:
            def __init__(self, status_code: int, payload):
                self.status_code = status_code
                self._payload = payload

            def json(self):
                return self._payload

            def raise_for_status(self):
                if self.status_code >= 300:
                    raise RuntimeError("http error")

        mock_get.side_effect = [
            _FakeResp(200, open_prs),
            _FakeResp(200, old_pr_files),
            _FakeResp(200, []),
        ]
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            "html_url": "https://github.com/TeaSui/swarmforge-session-dashboard/pull/2001",
            "number": 2001,
        }
        result = executor.execute_stage("SCRUM-1001", "code-generation", context)

    assert result["delivery"]["enabled"] is True
    assert result["delivery"].get("reused") is not True
    assert result["delivery"]["pr_number"] == 2001
