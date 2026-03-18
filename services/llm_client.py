from __future__ import annotations

import logging
import os
from typing import Any

try:
    from langchain_anthropic import ChatAnthropic
    from langchain_aws import ChatBedrock
    from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
except Exception:  # pragma: no cover - local fallback for environments without full AI deps
    ChatAnthropic = None  # type: ignore[assignment]
    ChatBedrock = None  # type: ignore[assignment]
    BaseMessage = Any  # type: ignore[misc,assignment]
    HumanMessage = Any  # type: ignore[misc,assignment]
    SystemMessage = Any  # type: ignore[misc,assignment]

from config import settings
from services.budget_manager import BudgetExceededError, budget_manager

logger = logging.getLogger(__name__)

PRICING_PER_MILLION = {
    "sonnet": {"input": 3.0, "output": 15.0},
    "fallback": {"input": 3.0, "output": 15.0},
}


class _FallbackLLM:
    async def ainvoke(self, messages: list) -> Any:
        raise RuntimeError("LLM dependencies are not installed in this environment")


class LLMClient:
    def __init__(self) -> None:
        self._initialized = False
        self.primary_llm: Any = _FallbackLLM()
        self.fallback_llm: Any = _FallbackLLM()
        self.primary_name = "unavailable"
        self.fallback_name = "unavailable"

    def _ensure_initialized(self) -> None:
        """Lazy initialization to avoid import-time AWS calls."""
        if self._initialized:
            return
        self._initialized = True

        if ChatAnthropic is None or ChatBedrock is None:
            return

        primary_choice = os.getenv("SWARMFORGE_PRIMARY_LLM", "").strip().lower()
        use_bedrock_primary = primary_choice == "bedrock"
        bedrock_model_id = os.getenv(
            "SWARMFORGE_BEDROCK_MODEL_ID",
            "global.anthropic.claude-sonnet-4-6",
        ).strip()

        timeout = settings.LLM_REQUEST_TIMEOUT_SECONDS
        max_tokens = settings.LLM_MAX_TOKENS

        from botocore.config import Config as BotoConfig
        from services.aws_session import get_boto3_session
        get_boto3_session()

        bedrock_llm = ChatBedrock(
            model_id=bedrock_model_id,
            region_name=settings.AWS_REGION,
            model_kwargs={"temperature": 0},
            credentials_profile_name=None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=BotoConfig(read_timeout=timeout),
        )
        anthropic_model = os.getenv(
            "SWARMFORGE_ANTHROPIC_MODEL_ID",
            "claude-sonnet-4-6",
        ).strip()
        anthropic_llm = ChatAnthropic(
            model=anthropic_model,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            temperature=0,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        if use_bedrock_primary:
            self.primary_llm = bedrock_llm
            self.fallback_llm = anthropic_llm
            self.primary_name = f"bedrock:{bedrock_model_id}"
            self.fallback_name = f"anthropic:{anthropic_model}"
        else:
            self.primary_llm = anthropic_llm
            self.fallback_llm = bedrock_llm
            self.primary_name = f"anthropic:{anthropic_model}"
            self.fallback_name = f"bedrock:{bedrock_model_id}"

    async def _track_usage(self, response: Any, model_key: str) -> None:
        """Extracts usage metadata and updates budget manager."""
        usage = getattr(response, "usage_metadata", None) or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        pricing = PRICING_PER_MILLION.get(model_key, {"input": 3.0, "output": 15.0})
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        await budget_manager.add_usage(input_tokens + output_tokens, cost)

    async def chat(self, messages: list) -> Any:
        """Executes a chat completion with automatic failover and budget enforcement."""
        self._ensure_initialized()

        try:
            logger.info("Attempting chat with primary LLM (%s)", self.primary_name)
            response = await self.primary_llm.ainvoke(messages)
            await self._track_usage(response, "sonnet")
            return response
        except BudgetExceededError:
            raise
        except (RuntimeError, ConnectionError, TimeoutError, OSError) as exc:
            logger.warning(
                "Primary LLM failed (%s: %s). Falling back to %s.",
                type(exc).__name__, exc, self.fallback_name,
            )
        except Exception as exc:
            logger.warning(
                "Primary LLM unexpected failure (%s: %s). Falling back to %s.",
                type(exc).__name__, exc, self.fallback_name,
            )

        try:
            response = await self.fallback_llm.ainvoke(messages)
            await self._track_usage(response, "fallback")
            return response
        except BudgetExceededError:
            raise
        except Exception as exc:
            logger.critical("Fallback LLM also failed: %s: %s", type(exc).__name__, exc)
            raise


# Singleton instance
llm_client = LLMClient()
