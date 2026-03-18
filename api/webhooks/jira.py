import hashlib
import hmac
import logging
from uuid import uuid4

from api.webhooks.shared import MAX_PAYLOAD_BYTES, publish_to_queue
from config import settings
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from models.webhook_payload import JiraWebhookPayload
from services.idempotency import idempotency_service
from services.logging_setup import set_correlation_id

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_jira_signature(payload_bytes: bytes, signature_header: str | None) -> None:
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256")

    if signature_header.startswith("sha256="):
        signature_header = signature_header[7:]

    expected = hmac.new(
        settings.JIRA_WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")


def _is_ai_task(payload: JiraWebhookPayload) -> bool:
    if not payload.issue or not payload.issue.fields.labels:
        return False
    labels = set(payload.issue.fields.labels)
    return not labels.isdisjoint(settings.ai_labels_set)


@router.post("/jira")
async def jira_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(None),
):
    correlation_id = str(uuid4())
    set_correlation_id(correlation_id)

    body = await request.body()
    if len(body) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")

    _validate_jira_signature(body, x_hub_signature_256)

    try:
        payload_dict = await request.json()
        payload = JiraWebhookPayload(**payload_dict)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse Jira payload: {exc}") from None

    if _is_ai_task(payload):
        dedupe_key = f"jira:{payload.issue.id}:{payload.webhookEvent}"

        if await idempotency_service.is_duplicate(dedupe_key):
            logger.debug("Duplicate Jira event ignored: %s", dedupe_key)
            return {"status": "ignored", "reason": "duplicate", "source": "jira"}

        background_tasks.add_task(
            publish_to_queue,
            payload_dict,
            "jira",
            payload.webhookEvent,
            correlation_id,
        )

    return {"status": "accepted", "source": "jira"}
