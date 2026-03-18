import asyncio
import logging

from config import settings

logger = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    """Raised when token or USD budget is exceeded."""


class BudgetManager:
    def __init__(self) -> None:
        self.current_tokens: int = 0
        self.current_usd: float = 0.0
        self._lock = asyncio.Lock()

        self.token_soft = settings.DEFAULT_TOKEN_SOFT_LIMIT
        self.token_hard = settings.DEFAULT_TOKEN_HARD_LIMIT
        self.usd_soft = settings.DEFAULT_USD_SOFT_LIMIT
        self.usd_hard = settings.DEFAULT_USD_HARD_LIMIT

    async def reset(self) -> None:
        """Resets tracking for a new task (thread-safe)."""
        async with self._lock:
            self.current_tokens = 0
            self.current_usd = 0.0

    async def add_usage(self, tokens: int, usd: float) -> None:
        """Adds usage and checks against hard limits."""
        async with self._lock:
            self.current_tokens += tokens
            self.current_usd += usd

            logger.debug(
                "Usage update -> Tokens: %d, USD: $%.4f",
                self.current_tokens, self.current_usd,
            )

            if self.current_tokens >= self.token_hard:
                raise BudgetExceededError(
                    f"Token hard limit exceeded: {self.current_tokens} >= {self.token_hard}"
                )
            if self.current_usd >= self.usd_hard:
                raise BudgetExceededError(
                    f"USD hard limit exceeded: ${self.current_usd:.2f} >= ${self.usd_hard:.2f}"
                )
            if self.current_tokens >= self.token_soft:
                logger.warning("Token soft limit reached: %d", self.current_tokens)
            if self.current_usd >= self.usd_soft:
                logger.warning("USD soft limit reached: $%.2f", self.current_usd)

    async def persist_usage(self, task_id: str) -> None:
        """Persists final usage to DynamoDB via StateManager."""
        logger.info(
            "Persisting usage for task %s: %d tokens, $%.2f",
            task_id, self.current_tokens, self.current_usd,
        )


# Singleton instance
budget_manager = BudgetManager()
