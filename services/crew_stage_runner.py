from __future__ import annotations

import logging
import os
import time
from typing import Any

from services import agents as agents_module

try:
    from crewai import Crew, Process, Task
except Exception:  # pragma: no cover - fallback for local environments
    Crew = None  # type: ignore[assignment]
    Process = None  # type: ignore[assignment]
    Task = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class CrewStageRunner:
    def __init__(self):
        try:
            attempts = int(os.getenv("SWARMFORGE_CREW_STAGE_ATTEMPTS", "3"))
        except ValueError:
            attempts = 3
        try:
            backoff = float(os.getenv("SWARMFORGE_CREW_STAGE_RETRY_BACKOFF_SECONDS", "6"))
        except ValueError:
            backoff = 6.0

        self.max_attempts = max(1, attempts)
        self.base_backoff_seconds = max(1.0, backoff)
        self.fallback_model = os.getenv(
            "SWARMFORGE_CREW_FALLBACK_MODEL",
            "anthropic/claude-haiku-4-5-20251001",
        ).strip()

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        message = str(exc).lower()
        needles = (
            "read timeout",
            "timed out",
            "connection error",
            "temporarily unavailable",
            "service unavailable",
            "too many requests",
            "throttl",
            "rate exceeded",
        )
        return any(token in message for token in needles)

    @staticmethod
    def _is_throttled_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "too many tokens per day" in message or "throttl" in message

    @staticmethod
    def _switch_model(model: str):
        os.environ["SWARMFORGE_CREW_MODEL"] = model
        # Force rebuilding agents so llm target is reapplied.
        agents_module.agent_pool.clear()
        logger.warning("Switched Crew model override to %s due to runtime pressure", model)

    def run(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        entries = agents_module.get_stage_agents(stage)
        if not entries:
            return {"mode": "none", "agents": [], "output": ""}

        descriptions = [
            f"Stage: {stage}",
            f"Summary: {context.get('summary', '')}",
            f"Labels: {', '.join(context.get('labels', [])) or 'none'}",
            f"Source: {context.get('source', 'unknown')}",
        ]
        description = "\n".join(descriptions)
        expected = f"Actionable output for stage {stage}"

        # Prefer real CrewAI kickoff when available.
        if Crew and Task and Process:
            last_exc: Exception | None = None
            for attempt in range(1, self.max_attempts + 1):
                try:
                    entries = agents_module.get_stage_agents(stage)
                    crew_agents = []
                    tasks = []
                    for spec, adapter in entries:
                        resolved_agent = getattr(adapter, "_resolve", lambda: None)()
                        crew_agent = getattr(resolved_agent, "agent", None)
                        if crew_agent is None:
                            continue
                        crew_agents.append(crew_agent)
                        tasks.append(
                            Task(
                                description=description,
                                expected_output=expected,
                                agent=crew_agent,
                            )
                        )
                    if crew_agents and tasks:
                        crew = Crew(
                            agents=crew_agents,
                            tasks=tasks,
                            process=Process.sequential,
                            verbose=False,
                        )
                        result = crew.kickoff()
                        return {
                            "mode": "crewai",
                            "agents": [spec.extension_id for spec, _ in entries],
                            "output": str(result),
                        }
                except Exception as exc:
                    last_exc = exc
                    retryable = self._is_retryable_error(exc)
                    if self.fallback_model and self._is_throttled_error(exc):
                        current_override = os.getenv("SWARMFORGE_CREW_MODEL", "").strip()
                        if current_override != self.fallback_model:
                            self._switch_model(self.fallback_model)
                    if attempt >= self.max_attempts or not retryable:
                        raise
                    delay = self.base_backoff_seconds * (2 ** (attempt - 1))
                    logger.warning(
                        "Crew stage %s failed attempt %s/%s with retryable error: %s; retry in %.1fs",
                        stage,
                        attempt,
                        self.max_attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
            if last_exc:
                raise last_exc

        # Fallback: still execute through registered real adapters.
        outputs = []
        for spec, adapter in entries:
            outputs.append(
                {
                    "extension_id": spec.extension_id,
                    "result": adapter.execute_task(description, context=[context]),
                }
            )
        return {"mode": "adapter", "agents": [o["extension_id"] for o in outputs], "output": outputs}
