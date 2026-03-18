import logging
import os
from typing import Any

try:
    from crewai import LLM, Agent
except Exception:  # pragma: no cover - fallback for unsupported local Python versions
    class Agent:  # type: ignore[override]
        def __init__(self, **kwargs):
            self.role = kwargs.get("role", "SwarmAgent")
            self.goal = kwargs.get("goal", "")
    LLM = None  # type: ignore[assignment]
try:
    from langchain_core.tools import BaseTool
except Exception:  # pragma: no cover - lightweight fallback for local test imports
    BaseTool = Any  # type: ignore[misc,assignment]
from config import settings

logger = logging.getLogger(__name__)


def _crew_llm_target() -> str:
    override = os.getenv("SWARMFORGE_CREW_MODEL", "").strip()
    if override:
        return override
    primary = os.getenv("SWARMFORGE_PRIMARY_LLM", "").strip().lower()
    if primary == "bedrock":
        return "bedrock/global.anthropic.claude-sonnet-4-6"
    anthropic_model = os.getenv("SWARMFORGE_ANTHROPIC_MODEL_ID", "claude-sonnet-4-6").strip()
    return f"anthropic/{anthropic_model}"


def _crew_llm_config() -> str | Any:
    target = _crew_llm_target()
    if LLM is None:
        return target

    try:
        timeout_seconds = float(os.getenv("SWARMFORGE_CREW_LLM_TIMEOUT_SECONDS", "120"))
    except ValueError:
        timeout_seconds = 120.0
    try:
        max_tokens = int(os.getenv("SWARMFORGE_CREW_MAX_TOKENS", "1200"))
    except ValueError:
        max_tokens = 1200
    try:
        max_retries = int(os.getenv("SWARMFORGE_CREW_MAX_RETRIES", "2"))
    except ValueError:
        max_retries = 2
    llm_kwargs = {
        "model": target,
        "timeout": timeout_seconds,
        "temperature": 0,
        "max_tokens": max_tokens,
        "max_retries": max_retries,
    }
    try:
        return LLM(**llm_kwargs)
    except Exception as exc:
        logger.warning("Failed to build CrewAI LLM config for %s: %s", target, exc)
        return target


class BaseSwarmAgent:
    """Base class for all SwarmForge agents, wrapping CrewAI Agent with custom behavior."""

    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        tools: list[BaseTool] | None = None,
        verbose: bool = True,
        allow_delegation: bool = False,
    ):
        if settings.ANTHROPIC_API_KEY:
            os.environ.setdefault("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY)

        agent_kwargs = dict(
            role=role,
            goal=goal,
            backstory=backstory,
            tools=tools or [],
            verbose=verbose,
            allow_delegation=allow_delegation,
            llm=_crew_llm_config(),
        )
        try:
            self.agent = Agent(**agent_kwargs)
        except (TypeError, RuntimeError) as exc:
            logger.warning(
                "Agent init with tools failed for role=%s; retrying without tools. error=%s",
                role,
                exc,
            )
            agent_kwargs["tools"] = []
            self.agent = Agent(**agent_kwargs)

    def execute_task(self, task_description: str, context: list[Any] | None = None) -> str:
        context = context or []
        if hasattr(self.agent, "execute_task"):
            try:
                output = self.agent.execute_task(task_description)
                return str(output)
            except (RuntimeError, AttributeError, TypeError) as exc:
                logger.warning(
                    "Agent.execute_task failed for role=%s: %s: %s",
                    self.agent.role, type(exc).__name__, exc,
                )
        if hasattr(self.agent, "kickoff"):
            try:
                output = self.agent.kickoff(task=task_description)
                return str(output)
            except (RuntimeError, AttributeError, TypeError) as exc:
                logger.warning(
                    "Agent.kickoff failed for role=%s: %s: %s",
                    self.agent.role, type(exc).__name__, exc,
                )
        context_blob = " | ".join(str(item) for item in context[:5])
        return f"[{self.agent.role}] fallback execution: {task_description}" + (
            f" | context: {context_blob}" if context_blob else ""
        )


class AgentMemory:
    """Simple memory system for inter-agent context."""

    def __init__(self):
        self.context_store: dict[str, Any] = {}

    def save(self, key: str, value: Any) -> None:
        self.context_store[key] = value

    def get(self, key: str) -> Any | None:
        return self.context_store.get(key)
