from __future__ import annotations

import logging
import os
from functools import lru_cache

import boto3
from botocore.exceptions import ProfileNotFound
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

REQUIRED_SECRETS = [
    "JIRA_WEBHOOK_SECRET",
    "SLACK_SIGNING_SECRET",
    "GENERIC_WEBHOOK_TOKEN",
    "ANTHROPIC_API_KEY",
    "JIRA_API_TOKEN",
    "GITHUB_TOKEN",
]

PLACEHOLDER_VALUES = {"", "placeholder", "dev_secret", "dev_token", "sk-ant-...", "jira_token", "github_token"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
    APP_ENV: str = "local"
    AWS_PROFILE: str = ""
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "ap-southeast-1"
    AWS_ENDPOINT_URL: str | None = None
    CLOUDWATCH_ENABLED: bool = False
    CLOUDWATCH_LOG_LEVEL: str = "INFO"
    CLOUDWATCH_LOG_GROUP_API: str = "/swarmforge/ecs/api"
    CLOUDWATCH_LOG_GROUP_WORKER: str = "/swarmforge/ecs/worker"
    SQS_QUEUE_URL: str = ""
    DYNAMODB_IDEMPOTENCY_TABLE: str = "swarmforge-idempotency"
    JIRA_WEBHOOK_SECRET: str = ""
    SLACK_SIGNING_SECRET: str = ""
    GENERIC_WEBHOOK_TOKEN: str = ""
    AI_TRIGGER_LABELS: str = "ai-task,ai,swarmforge"
    VERSION: str = "0.1.0"
    ANTHROPIC_API_KEY: str = ""
    SWARMFORGE_PRIMARY_LLM: str = "anthropic"
    SWARMFORGE_ANTHROPIC_MODEL_ID: str = "claude-sonnet-4-6"
    LANGSMITH_API_KEY: str | None = None
    LANGSMITH_PROJECT: str = "swarmforge"
    DEFAULT_TOKEN_SOFT_LIMIT: int = 100_000
    DEFAULT_TOKEN_HARD_LIMIT: int = 140_000
    DEFAULT_USD_SOFT_LIMIT: float = 4.0
    DEFAULT_USD_HARD_LIMIT: float = 6.0
    SWARMFORGE_QUALITY_GATES_ENABLED: bool = True
    JIRA_BASE_URL: str = "https://your-domain.atlassian.net"
    JIRA_EMAIL: str = "user@domain.com"
    JIRA_API_TOKEN: str = ""
    GITHUB_TOKEN: str = ""
    SWARMFORGE_TARGET_REPO: str = "TeaSui/swarmforge-session-dashboard"
    SLACK_WEBHOOK_URL: str | None = None
    APPROVAL_POLL_INTERVAL_SECONDS: int = 15
    APPROVAL_TIMEOUT_SECONDS: int = 900
    RATE_LIMIT_PER_MINUTE: int = 60

    # SQS consumer tuning
    SQS_LONG_POLL_WAIT_SECONDS: int = 20
    SQS_MAX_MESSAGES_PER_POLL: int = 10
    SQS_RETRY_BASE_SECONDS: float = 1.0
    SQS_RETRY_MAX_SECONDS: float = 60.0

    # LLM configuration
    LLM_REQUEST_TIMEOUT_SECONDS: int = 120
    LLM_MAX_TOKENS: int = 4096

    # Notification retry
    NOTIFICATION_MAX_ATTEMPTS: int = 3

    @property
    def ai_labels_set(self) -> set[str]:
        return set(self.AI_TRIGGER_LABELS.split(","))

    def validate_secrets(self) -> None:
        if self.APP_ENV in {"local", "test"}:
            return
        missing = [
            name for name in REQUIRED_SECRETS
            if getattr(self, name, "") in PLACEHOLDER_VALUES
        ]
        if missing:
            raise ValueError(
                f"Required secrets not configured for APP_ENV={self.APP_ENV}: {', '.join(missing)}"
            )

    def load_cloud_secrets(self) -> None:
        """Fetches secrets from AWS Secrets Manager in non-local environments."""
        if self.APP_ENV in {"local", "test"}:
            return

        try:
            import json

            if os.environ.get("AWS_PROFILE", None) == "":
                os.environ.pop("AWS_PROFILE", None)

            if self.AWS_ACCESS_KEY_ID and self.AWS_SECRET_ACCESS_KEY:
                session = boto3.Session(
                    aws_access_key_id=self.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY,
                    region_name=self.AWS_REGION,
                )
            elif self.AWS_PROFILE.strip():
                session = boto3.Session(
                    profile_name=self.AWS_PROFILE.strip(),
                    region_name=self.AWS_REGION,
                )
            else:
                session = boto3.Session(region_name=self.AWS_REGION)

            client = session.client("secretsmanager")
            response = client.get_secret_value(SecretId="SwarmForgeSecrets")
            secrets = json.loads(response["SecretString"])

            if "JIRA_API_TOKEN" in secrets:
                self.JIRA_API_TOKEN = secrets["JIRA_API_TOKEN"]
            if "ANTHROPIC_API_KEY" in secrets:
                self.ANTHROPIC_API_KEY = secrets["ANTHROPIC_API_KEY"]
            if "GITHUB_TOKEN" in secrets:
                self.GITHUB_TOKEN = secrets["GITHUB_TOKEN"]

            logger.info("Successfully loaded secrets from AWS Secrets Manager")
        except ProfileNotFound:
            logger.warning("AWS profile not found. Skipping cloud secrets load.")
        except Exception as exc:
            logger.warning("Failed to load secrets from Secrets Manager: %s", exc)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.load_cloud_secrets()
    s.validate_secrets()
    return s


class _LazySettings:
    """Lazy proxy that defers Settings instantiation until first attribute access.

    This avoids calling AWS Secrets Manager at module import time, which would
    cause import failures when AWS credentials are unavailable (e.g. in tests
    or CI environments that set APP_ENV before importing).
    """

    def __getattr__(self, name: str):
        real = get_settings()
        # Replace self in the module namespace so future accesses are direct.
        import config
        config.settings = real
        return getattr(real, name)


settings: Settings = _LazySettings()  # type: ignore[assignment]
