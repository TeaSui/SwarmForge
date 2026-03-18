"""Shared utilities for webhook handlers."""
from __future__ import annotations

import logging

from models.sqs_message import SQSMessageEnvelope
from services.sqs_producer import sqs_producer

logger = logging.getLogger(__name__)

# Maximum accepted webhook payload size (1 MB).
MAX_PAYLOAD_BYTES = 1_048_576


async def publish_to_queue(
    payload: dict,
    source: str,
    event_type: str,
    correlation_id: str = "",
) -> None:
    """Publish a validated webhook payload to the SQS task queue."""
    envelope = SQSMessageEnvelope(
        source=source,
        event_type=event_type,
        payload=payload,
        metadata={"correlation_id": correlation_id},
    )
    success = await sqs_producer.publish(envelope)
    if not success:
        logger.critical("Failed to publish %s event to SQS", source)
