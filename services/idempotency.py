from __future__ import annotations

import logging
from datetime import UTC, datetime

from botocore.exceptions import BotoCoreError, ClientError
from config import settings
from services.aws_session import get_aws_client

logger = logging.getLogger(__name__)


class IdempotencyStore:
    """Unified DynamoDB-backed idempotency and deduplication service.

    Replaces the former separate DynamoDBDeduplicator and IdempotencyService
    classes with a single implementation.
    """

    def __init__(self, table_name: str, region: str):
        self.table_name = table_name
        self.region = region
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_aws_client("dynamodb", region_name=self.region)
        return self._client

    def _try_insert(self, key: str, ttl_seconds: int) -> bool:
        """Attempt conditional insert. Returns True if the key was new."""
        now = datetime.now(UTC)
        expires_at = int(now.timestamp()) + ttl_seconds
        try:
            self.client.put_item(
                TableName=self.table_name,
                Item={
                    "idempotency_key": {"S": key},
                    "created_at": {"S": now.isoformat()},
                    "expires_at": {"N": str(expires_at)},
                },
                ConditionExpression="attribute_not_exists(idempotency_key)",
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.info("Duplicate event suppressed: %s", key[:32])
                return False
            logger.warning("DynamoDB error in idempotency check (failing open): %s", exc)
            return True
        except BotoCoreError as exc:
            logger.warning("DynamoDB infrastructure error (failing open): %s", exc)
            return True

    # -- Public API (async, used by webhook handlers) ----------------------

    async def is_duplicate(self, key: str, ttl_hours: int = 24) -> bool:
        ttl_seconds = ttl_hours * 3600
        return not self._try_insert(key, ttl_seconds)

    # -- Public API (sync, used by deduplication consumers) ----------------

    def is_new_event(self, key: str, ttl_seconds: int = 3600) -> bool:
        return self._try_insert(key, ttl_seconds)


# Singleton instance
idempotency_store = IdempotencyStore(
    table_name=settings.DYNAMODB_IDEMPOTENCY_TABLE,
    region=settings.AWS_REGION,
)

# Backwards-compatible aliases
idempotency_service = idempotency_store
