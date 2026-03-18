import asyncio
import json
import logging
import random
from collections.abc import Awaitable, Callable

from botocore.exceptions import ClientError
from config import settings
from services.aws_session import get_aws_client

logger = logging.getLogger(__name__)


class SQSConsumer:
    def __init__(self, queue_url: str, handler: Callable[[dict], Awaitable[None]]):
        self.sqs = get_aws_client("sqs")
        self.queue_url = queue_url
        self.handler = handler
        self.is_running = False

    async def start(self) -> None:
        """Starts the SQS long-polling loop with exponential backoff on errors."""
        self.is_running = True
        logger.info("SQS Consumer started for %s", self.queue_url)

        consecutive_errors = 0

        while self.is_running:
            try:
                response = self.sqs.receive_message(
                    QueueUrl=self.queue_url,
                    AttributeNames=["All"],
                    MaxNumberOfMessages=settings.SQS_MAX_MESSAGES_PER_POLL,
                    WaitTimeSeconds=settings.SQS_LONG_POLL_WAIT_SECONDS,
                )

                messages = response.get("Messages", [])
                if not messages:
                    consecutive_errors = 0
                    continue

                for message in messages:
                    await self._process_message(message)
                consecutive_errors = 0

            except ClientError as exc:
                consecutive_errors += 1
                delay = self._backoff_delay(consecutive_errors)
                logger.error("SQS ClientError (retry in %.1fs): %s", delay, exc)
                await asyncio.sleep(delay)
            except Exception as exc:
                consecutive_errors += 1
                delay = self._backoff_delay(consecutive_errors)
                logger.error(
                    "SQS unexpected error %s (retry in %.1fs): %s",
                    type(exc).__name__, delay, exc,
                )
                await asyncio.sleep(delay)

    async def stop(self) -> None:
        self.is_running = False

    def _backoff_delay(self, consecutive_errors: int) -> float:
        """Exponential backoff with jitter, capped at SQS_RETRY_MAX_SECONDS."""
        base = settings.SQS_RETRY_BASE_SECONDS
        cap = settings.SQS_RETRY_MAX_SECONDS
        delay = min(base * (2 ** (consecutive_errors - 1)), cap)
        jitter = random.uniform(0, delay * 0.25)
        return delay + jitter

    async def _process_message(self, message: dict) -> None:
        receipt_handle = message["ReceiptHandle"]
        body = message["Body"]
        message_id = message.get("MessageId", "unknown")

        try:
            payload = json.loads(body)
            await self.handler(payload)

            await asyncio.to_thread(
                self.sqs.delete_message,
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )
        except json.JSONDecodeError as exc:
            logger.error(
                "Malformed SQS message body %s: %s", message_id, exc,
                extra={"message_id": message_id},
            )
        except Exception as exc:
            logger.error(
                "Failed to process SQS message %s (%s): %s",
                message_id, type(exc).__name__, exc,
                extra={"message_id": message_id, "receipt_handle": receipt_handle[:20]},
            )
