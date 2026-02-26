# Phase 1: Ingress & Queue — Research

**Phase:** 1 — Ingress & Queue
**Researched:** 2026-02-26
**Goal:** Accept triggers from Jira, Slack, and generic webhooks; buffer via SQS; deduplicate.

## RESEARCH COMPLETE

---

## 1. FastAPI Webhook Design (2025 Patterns)

### Recommended Stack
- **Framework:** FastAPI 0.115+ with `uvicorn[standard]` ASGI server
- **Validation:** Pydantic v2 models for all webhook payloads (breaking changes from v1 — use `model_validator`)
- **Background processing:** FastAPI `BackgroundTasks` for async SQS publish (keeps 200ms response SLA)

### Webhook Security
- **Jira webhooks**: Validate `X-Hub-Signature` HMAC-SHA256 header (configured in Jira webhook settings)
- **Slack webhooks**: Validate `X-Slack-Signature` with `X-Slack-Request-Timestamp` (replay protection)
- **Generic webhooks**: Accept configurable HMAC or bearer token, reject unsigned requests

### Response Pattern — Keep Under 200ms
```python
@app.post("/webhook/jira")
async def jira_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    # 1. Validate signature synchronously (fast)
    await validate_jira_signature(request)
    # 2. Parse payload synchronously
    payload = await request.json()
    # 3. Publish to SQS asynchronously (non-blocking)
    background_tasks.add_task(publish_to_sqs, payload, source="jira")
    # 4. Return immediate ack
    return {"status": "accepted"}
```

### Jira Webhook Payload Filtering
Jira sends events for ALL issue changes. Filter to only AI-labelled issues:
```python
def is_ai_task(payload: dict) -> bool:
    labels = payload.get("issue", {}).get("fields", {}).get("labels", [])
    return any(l.get("name") in AI_TRIGGER_LABELS for l in labels)
```
`AI_TRIGGER_LABELS = {"ai-task", "ai", "swarmforge"}` (configurable via env)

### Health Check
```python
@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}
```

---

## 2. SQS Integration (aiobotocore vs boto3)

### Library Choice
- **Use `boto3` with thread pool** (not `aiobotocore`) — simpler dependency tree, `BackgroundTasks` handles async without event loop complexity
- AWS SDK recommendation for ECS Fargate: boto3 + `botocore` with connection pooling

### SQS Message Format
```python
import boto3, json, uuid
from datetime import datetime, UTC

sqs = boto3.client("sqs", region_name=settings.AWS_REGION)

def publish_to_sqs(payload: dict, source: str) -> str:
    message = {
        "task_id": str(uuid.uuid4()),
        "source": source,           # "jira" | "slack" | "generic"
        "event_type": payload.get("webhookEvent", "unknown"),
        "idempotency_key": build_idempotency_key(payload, source),
        "received_at": datetime.now(UTC).isoformat(),
        "payload": payload,
    }
    response = sqs.send_message(
        QueueUrl=settings.SQS_QUEUE_URL,
        MessageBody=json.dumps(message),
        MessageGroupId=source,          # FIFO queue grouping (if FIFO)
        MessageDeduplicationId=message["idempotency_key"],  # FIFO dedup
    )
    return response["MessageId"]
```

### Standard vs FIFO Queue
| | Standard Queue | FIFO Queue |
|--|--|--|
| Ordering | Not guaranteed | Guaranteed per group |
| Deduplication | Must implement in app | Native (5-min window) |
| Throughput | Unlimited | 3,000 msg/sec |
| **Recommendation** | ✓ **Use Standard + app-level dedup** | Overkill for current scale |

**Decision: Standard SQS queue** — lower cost, higher throughput, implement dedup in DynamoDB.

### DLQ Configuration
```python
# CDK (Phase 5), but document here for Phase 1 service:
# - DLQ receives messages after maxReceiveCount = 3 failed attempts
# - DLQ retention: 14 days (time to debug + replay)
# - Main queue visibility timeout: 30 minutes (long enough for agent run)
```

---

## 3. Deduplication Strategy

### Idempotency Key Construction
```python
def build_idempotency_key(payload: dict, source: str) -> str:
    if source == "jira":
        issue_id = payload.get("issue", {}).get("id", "")
        event_type = payload.get("webhookEvent", "")
        timestamp = payload.get("timestamp", "")
        # Include hour bucket to allow same event type to re-trigger after 1h
        hour_bucket = timestamp[:13] if timestamp else ""
        raw = f"jira:{issue_id}:{event_type}:{hour_bucket}"
    elif source == "slack":
        raw = f"slack:{payload.get('event_id', uuid.uuid4())}"
    else:
        raw = f"generic:{payload.get('id', uuid.uuid4())}"
    return hashlib.sha256(raw.encode()).hexdigest()
```

### DynamoDB Idempotency Table
```python
# Table: swarmforge-idempotency
# PK: idempotency_key (String)
# TTL: expires_at (Number, epoch seconds)
# TTL window: 1 hour (prevents exact duplicate re-processing)

import time

def check_and_mark_idempotent(key: str) -> bool:
    """Returns True if this is a NEW event (process it). False = duplicate (skip)."""
    try:
        dynamodb.put_item(
            TableName=settings.IDEMPOTENCY_TABLE,
            Item={
                "idempotency_key": {"S": key},
                "created_at": {"S": datetime.now(UTC).isoformat()},
                "expires_at": {"N": str(int(time.time()) + 3600)},  # 1h TTL
            },
            ConditionExpression="attribute_not_exists(idempotency_key)",
        )
        return True  # New event
    except dynamodb.exceptions.ConditionalCheckFailedException:
        return False  # Duplicate
```

**Why DynamoDB over Redis?**
- No additional infra to manage in Phase 1 (Redis = Phase 2+ if needed)
- DynamoDB TTL handles cleanup automatically
- Already needed for task state in Phase 2 — consistent choice

---

## 4. Project Structure (Phase 1 Files)

```
swarmforge/
├── main.py                     # FastAPI app entry point
├── config.py                   # Settings via pydantic-settings
├── api/
│   ├── __init__.py
│   ├── webhooks/
│   │   ├── __init__.py
│   │   ├── jira.py             # /webhook/jira route
│   │   ├── slack.py            # /webhook/slack route
│   │   └── generic.py          # /webhook/generic route
│   └── health.py               # /health route
├── services/
│   ├── __init__.py
│   ├── sqs_producer.py         # SQS publish logic
│   └── deduplication.py        # DynamoDB idempotency check
├── models/
│   ├── __init__.py
│   └── webhook_payload.py      # Pydantic v2 models
├── tests/
│   ├── test_webhooks.py
│   ├── test_sqs_producer.py
│   └── test_deduplication.py
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## 5. Dependencies

```txt
# requirements.txt (Phase 1)
fastapi==0.115.6
uvicorn[standard]==0.32.1
pydantic==2.10.4
pydantic-settings==2.7.0
boto3==1.35.91
httpx==0.28.1       # For async health checks / testing
python-dotenv==1.0.1
pytest==8.3.4
pytest-asyncio==0.24.0
moto[sqs,dynamodb]==5.0.21  # AWS mock for testing
```

---

## 6. Environment Variables

```bash
# .env.example
APP_ENV=local                      # local | staging | production
AWS_REGION=ap-southeast-1
SQS_QUEUE_URL=https://sqs.{region}.amazonaws.com/{account}/{queue-name}
DYNAMODB_IDEMPOTENCY_TABLE=swarmforge-idempotency
JIRA_WEBHOOK_SECRET=your-jira-webhook-secret
SLACK_SIGNING_SECRET=your-slack-signing-secret
AI_TRIGGER_LABELS=ai-task,ai,swarmforge
VERSION=0.1.0
```

---

## 7. Pitfalls to Avoid

| Pitfall | Prevention |
|---------|-----------|
| Jira sends events for ALL issues — easy to process noise | Always filter by AI label before publishing to SQS |
| 200ms SLA violated if SQS publish is synchronous | Use `BackgroundTasks` to publish SQS async after immediate ack |
| SQS `visibility_timeout` too short → message redelivered mid-processing | Set to 30min (Phase 2 sets this when consuming) |
| DynamoDB conditional write raises exception on duplicate — don't swallow | Catch `ConditionalCheckFailedException` specifically, return 200 (not 409) to Jira to prevent retry storms |
| Jira retries if it doesn't get 2xx within timeout | Always return 200 immediately, even for filtered (non-AI) events |
| Missing HMAC validation → security exposure | Validate ALL webhook signatures before parsing payload |
| `pydantic.v1` vs `pydantic.v2` import conflicts | Use `pydantic>=2.0` and `from pydantic import BaseModel` (not `v1`) |

---

## 8. Testing Approach

```python
# tests/test_webhooks.py — key test cases
# 1. Valid Jira webhook with AI label → 200, SQS publish called
# 2. Valid Jira webhook without AI label → 200, SQS publish NOT called
# 3. Invalid HMAC signature → 401
# 4. Duplicate Jira event → 200 (idempotent), SQS NOT published twice
# 5. SQS publish failure → 202 (accepted but warn log, don't fail webhook)
# 6. /health → 200 {"status": "ok"}

# Use moto for SQS/DynamoDB mocking — no real AWS needed in tests
```

---

*Phase: 01-ingress-queue*
*Research completed: 2026-02-26*
