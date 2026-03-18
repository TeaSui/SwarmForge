from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from services.executor.flutter_codegen import FlutterCodeGenerator
from services.executor.git_ops import GitOperations
from services.executor.github_delivery import GitHubDeliveryService
from services.executor.llm_codegen import LLMCodeSynthesizer
from services.executor.stage_dispatcher import StageDispatcher, StageExecutionError


class AutonomousExecutor:
    """Thin facade composing executor sub-modules."""

    def __init__(self, workspace_root: str | None = None, llm_synthesizer: LLMCodeSynthesizer | None = None):
        root = Path(workspace_root or Path.cwd()).resolve()
        git_ops = GitOperations(root)
        flutter = FlutterCodeGenerator()
        delivery = GitHubDeliveryService(git_ops, flutter)
        synthesizer = llm_synthesizer or LLMCodeSynthesizer()
        self._dispatcher = StageDispatcher(root, git_ops, delivery, synthesizer)

    def execute_stage(self, task_id: str, stage: str, context: dict[str, Any]) -> Dict[str, Any]:
        return self._dispatcher.execute_stage(task_id, stage, context)


__all__ = ["AutonomousExecutor", "StageExecutionError"]
