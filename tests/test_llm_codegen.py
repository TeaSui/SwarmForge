from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.executor.llm_codegen import (
    LLMCodeSynthesizer,
    SynthesizedCode,
    _extract_json,
)


class TestExtractJson:
    def test_extracts_plain_json(self):
        raw = '{"files": [], "summary": "test", "reasoning": "none"}'
        result = _extract_json(raw)
        assert result["summary"] == "test"

    def test_extracts_from_markdown_fences(self):
        raw = '```json\n{"files": [], "summary": "fenced"}\n```'
        result = _extract_json(raw)
        assert result["summary"] == "fenced"

    def test_extracts_from_bare_fences(self):
        raw = '```\n{"files": [{"path": "a.py", "content": "x"}]}\n```'
        result = _extract_json(raw)
        assert len(result["files"]) == 1

    def test_raises_on_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            _extract_json("not json at all")


class TestLLMCodeSynthesizer:
    @pytest.fixture()
    def mock_llm(self):
        client = MagicMock()
        client.chat = AsyncMock()
        return client

    @pytest.fixture()
    def synthesizer(self, mock_llm):
        return LLMCodeSynthesizer(llm_client=mock_llm)

    @pytest.fixture()
    def jira_context(self):
        return {
            "task_id": "SCRUM-42",
            "summary": "Add health check endpoint",
            "labels": ["ai-task", "backend"],
            "source": "jira",
            "payload": {
                "issue": {
                    "key": "SCRUM-42",
                    "fields": {
                        "summary": "Add health check endpoint",
                        "description": "Create a /health endpoint that returns service status",
                        "labels": ["ai-task", "backend"],
                    },
                }
            },
        }

    @pytest.mark.asyncio
    async def test_synthesize_returns_files(self, synthesizer, mock_llm, jira_context):
        llm_response = MagicMock()
        llm_response.content = json.dumps({
            "files": [
                {
                    "path": "api/health.py",
                    "content": "from fastapi import APIRouter\nrouter = APIRouter()\n@router.get('/health')\ndef health(): return {'status': 'ok'}",
                    "language": "python",
                },
                {
                    "path": "tests/test_health.py",
                    "content": "def test_health():\n    assert True",
                    "language": "python",
                },
            ],
            "summary": "Added health check endpoint with test",
            "reasoning": "Simple GET endpoint returning service status",
        })
        mock_llm.chat.return_value = llm_response

        result = await synthesizer.synthesize(jira_context)

        assert result.error is None
        assert len(result.files) == 2
        assert result.files[0]["path"] == "api/health.py"
        assert result.summary == "Added health check endpoint with test"
        mock_llm.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_handles_llm_failure(self, synthesizer, mock_llm, jira_context):
        mock_llm.chat.side_effect = RuntimeError("LLM unavailable")

        result = await synthesizer.synthesize(jira_context)

        assert result.error == "LLM unavailable"
        assert result.files == []

    @pytest.mark.asyncio
    async def test_synthesize_handles_malformed_json(self, synthesizer, mock_llm, jira_context):
        llm_response = MagicMock()
        llm_response.content = "Here is some code but not valid JSON"
        mock_llm.chat.return_value = llm_response

        result = await synthesizer.synthesize(jira_context)

        assert result.error is not None
        assert "JSON parse error" in result.error
        assert result.raw_response == "Here is some code but not valid JSON"

    @pytest.mark.asyncio
    async def test_synthesize_filters_empty_files(self, synthesizer, mock_llm, jira_context):
        llm_response = MagicMock()
        llm_response.content = json.dumps({
            "files": [
                {"path": "real.py", "content": "print('hello')", "language": "python"},
                {"path": "", "content": "orphan"},
                {"path": "empty.py", "content": ""},
            ],
            "summary": "partial",
            "reasoning": "test",
        })
        mock_llm.chat.return_value = llm_response

        result = await synthesizer.synthesize(jira_context)

        assert len(result.files) == 1
        assert result.files[0]["path"] == "real.py"

    @pytest.mark.asyncio
    async def test_synthesize_handles_markdown_fenced_response(self, synthesizer, mock_llm, jira_context):
        llm_response = MagicMock()
        llm_response.content = '```json\n{"files": [{"path": "a.py", "content": "x"}], "summary": "ok", "reasoning": "r"}\n```'
        mock_llm.chat.return_value = llm_response

        result = await synthesizer.synthesize(jira_context)

        assert result.error is None
        assert len(result.files) == 1

    def test_build_prompt_includes_ticket_context(self, synthesizer, jira_context):
        prompt = synthesizer._build_prompt(jira_context, "research notes")

        assert "SCRUM-42" in prompt
        assert "Add health check endpoint" in prompt
        assert "ai-task" in prompt
        assert "research notes" in prompt

    def test_build_description_handles_dict_description(self, synthesizer):
        context = {
            "summary": "fallback summary",
            "payload": {
                "issue": {
                    "fields": {
                        "description": {"type": "doc", "content": [{"text": "rich text"}]},
                    }
                }
            },
        }
        desc = synthesizer._build_description(context)
        assert "rich text" in desc


class TestStageDispatcherLLMIntegration:
    def test_codegen_writes_llm_files_to_delivery(self, tmp_path: Path):
        from services.autonomous_executor import AutonomousExecutor
        from services.executor.llm_codegen import SynthesizedCode

        synthesized = SynthesizedCode(
            files=[
                {"path": "lib/src/feature.dart", "content": "class Feature {}", "language": "dart"},
                {"path": "test/feature_test.dart", "content": "void main() {}", "language": "dart"},
            ],
            summary="Generated feature implementation",
            reasoning="Based on ticket requirements",
        )

        mock_synthesizer = MagicMock()
        mock_synthesizer._get_llm_client.return_value = MagicMock()

        executor = AutonomousExecutor(
            workspace_root=str(tmp_path),
            llm_synthesizer=mock_synthesizer,
        )

        context = {
            "source": "jira",
            "task_id": "SCRUM-50",
            "summary": "Build feature",
            "labels": [],
            "payload": {"issue": {"key": "SCRUM-50"}},
        }

        with patch.dict("os.environ", {
            "SWARMFORGE_GITHUB_DELIVERY_ENABLED": "true",
            "GITHUB_TOKEN": "test-token",
            "SWARMFORGE_LLM_CODEGEN_ENABLED": "true",
        }), patch.object(
            executor._dispatcher, "_run_llm_codegen", return_value=synthesized,
        ), patch.object(
            executor._dispatcher.git_ops, "run_git",
            return_value={"command": "git", "returncode": 0, "stdout_tail": "", "stderr_tail": ""},
        ), patch("services.executor.github_delivery.requests.get") as mock_get, \
             patch("services.executor.github_delivery.requests.post") as mock_post:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = []
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "html_url": "https://github.com/test/repo/pull/50",
                "number": 50,
            }

            result = executor.execute_stage("SCRUM-50", "code-generation", context)

        assert result["artifact"] == "CODEGEN.md"
        assert result.get("llm_synthesis", {}).get("files_count") == 2
        assert result["delivery"]["enabled"] is True

    def test_codegen_falls_back_when_llm_disabled(self, tmp_path: Path):
        from services.autonomous_executor import AutonomousExecutor

        executor = AutonomousExecutor(workspace_root=str(tmp_path))
        context = {
            "source": "jira",
            "task_id": "SCRUM-51",
            "summary": "Fallback test",
            "labels": [],
            "payload": {"issue": {"key": "SCRUM-51"}},
        }

        with patch.dict("os.environ", {
            "SWARMFORGE_GITHUB_DELIVERY_ENABLED": "true",
            "GITHUB_TOKEN": "test-token",
            "SWARMFORGE_LLM_CODEGEN_ENABLED": "false",
        }), patch.object(
            executor._dispatcher.git_ops, "run_git",
            return_value={"command": "git", "returncode": 0, "stdout_tail": "", "stderr_tail": ""},
        ), patch("services.executor.github_delivery.requests.get") as mock_get, \
             patch("services.executor.github_delivery.requests.post") as mock_post:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = []
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "html_url": "https://github.com/test/repo/pull/51",
                "number": 51,
            }

            result = executor.execute_stage("SCRUM-51", "code-generation", context)

        assert result["artifact"] == "CODEGEN.md"
        assert "llm_synthesis" not in result
        codegen_trace = (Path(result["run_dir"]) / "CODEGEN.md").read_text()
        assert "autonomous-executor" in codegen_trace

    def test_codegen_handles_llm_error_gracefully(self, tmp_path: Path):
        from services.autonomous_executor import AutonomousExecutor
        from services.executor.llm_codegen import SynthesizedCode

        failed_synthesis = SynthesizedCode(error="Connection timeout")
        mock_synthesizer = MagicMock()
        mock_synthesizer._get_llm_client.return_value = MagicMock()

        executor = AutonomousExecutor(
            workspace_root=str(tmp_path),
            llm_synthesizer=mock_synthesizer,
        )
        context = {
            "source": "jira",
            "task_id": "SCRUM-52",
            "summary": "Error handling test",
            "labels": [],
            "payload": {"issue": {"key": "SCRUM-52"}},
        }

        with patch.dict("os.environ", {
            "SWARMFORGE_GITHUB_DELIVERY_ENABLED": "true",
            "GITHUB_TOKEN": "test-token",
            "SWARMFORGE_LLM_CODEGEN_ENABLED": "true",
        }), patch.object(
            executor._dispatcher, "_run_llm_codegen", return_value=failed_synthesis,
        ), patch.object(
            executor._dispatcher.git_ops, "run_git",
            return_value={"command": "git", "returncode": 0, "stdout_tail": "", "stderr_tail": ""},
        ), patch("services.executor.github_delivery.requests.get") as mock_get, \
             patch("services.executor.github_delivery.requests.post") as mock_post:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = []
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "html_url": "https://github.com/test/repo/pull/52",
                "number": 52,
            }

            result = executor.execute_stage("SCRUM-52", "code-generation", context)

        assert result["artifact"] == "CODEGEN.md"
        assert result.get("llm_error") == "Connection timeout"
        assert result["delivery"]["enabled"] is True
