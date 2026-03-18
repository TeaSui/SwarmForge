import hashlib
import hmac
import logging
import time
from uuid import uuid4

from api.webhooks.shared import MAX_PAYLOAD_BYTES, publish_to_queue
from config import settings
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from services.idempotency import idempotency_service
from services.logging_setup import set_correlation_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum clock skew tolerance for Slack request timestamps.
_SLACK_TIMESTAMP_MAX_AGE_SECONDS = 60 * 5
_SLACK_TIMESTAMP_MAX_FUTURE_SECONDS = 60


def _validate_slack_signature(
    payload_bytes: bytes,
    timestamp: str | None,
    signature: str | None,
) -> None:
    if not timestamp or not signature:
        raise HTTPException(status_code=401, detail="Missing Slack signature or timestamp")

    try:
        ts_value = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Slack timestamp format") from None

    now = time.time()
    if now - ts_value > _SLACK_TIMESTAMP_MAX_AGE_SECONDS:
        raise HTTPException(status_code=401, detail="Slack request timestamp expired")
    if ts_value - now > _SLACK_TIMESTAMP_MAX_FUTURE_SECONDS:
        raise HTTPException(status_code=401, detail="Slack request timestamp too far in future")

    sig_basestring = f"v0:{timestamp}:".encode() + payload_bytes
    expected = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        sig_basestring,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")


@router.post("/slack")
async def slack_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_slack_request_timestamp: str | None = Header(None),
    x_slack_signature: str | None = Header(None),
):
    correlation_id = str(uuid4())
    set_correlation_id(correlation_id)

    body = await request.body()
    if len(body) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")

    _validate_slack_signature(body, x_slack_request_timestamp, x_slack_signature)

    payload = await request.json()

    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    event = payload.get("event", {})
    if event.get("type") == "app_mention" or "@ai" in event.get("text", "").lower():
        event_id = payload.get("event_id") or payload.get("event_time")
        dedupe_key = f"slack:{event_id}"

        if await idempotency_service.is_duplicate(dedupe_key):
            logger.debug("Duplicate Slack event ignored: %s", dedupe_key)
            return {"status": "ignored", "reason": "duplicate", "source": "slack"}

        background_tasks.add_task(
            publish_to_queue,
            payload,
            "slack",
            event.get("type", "unknown_event"),
            correlation_id,
        )

    return {"status": "accepted", "source": "slack"}
