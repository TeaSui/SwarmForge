import logging
from uuid import uuid4

from api.webhooks.shared import MAX_PAYLOAD_BYTES, publish_to_queue
from config import settings
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from services.idempotency import idempotency_service
from services.logging_setup import set_correlation_id

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != settings.GENERIC_WEBHOOK_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid generic webhook token")
    return credentials.credentials


@router.post("/generic")
async def generic_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    token: str = Depends(validate_token),
):
    correlation_id = str(uuid4())
    set_correlation_id(correlation_id)

    body = await request.body()
    if len(body) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")

    payload = await request.json()
    payload_id = payload.get("id")
    if payload_id:
        dedupe_key = f"generic:{payload_id}"
        if await idempotency_service.is_duplicate(dedupe_key):
            logger.debug("Duplicate Generic event ignored: %s", dedupe_key)
            return {"status": "ignored", "reason": "duplicate", "source": "generic"}

    background_tasks.add_task(
        publish_to_queue,
        payload,
        "generic",
        payload.get("event_type", "generic_event"),
        correlation_id,
    )

    return {"status": "accepted", "source": "generic"}
