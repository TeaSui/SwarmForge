import pytest
import hmac
import hashlib
import time
import json
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app
from config import settings


@pytest.fixture(autouse=True)
def mock_deps():
    with patch("api.webhooks.shared.sqs_producer") as mock_sqs_shared, \
         patch("api.webhooks.jira.idempotency_service") as mock_idx_jira, \
         patch("api.webhooks.slack.idempotency_service") as mock_idx_slack, \
         patch("api.webhooks.generic.idempotency_service") as mock_idx_generic:

        mock_sqs_shared.publish = AsyncMock(return_value=True)

        for m in [mock_idx_jira, mock_idx_slack, mock_idx_generic]:
            m.is_duplicate = AsyncMock(return_value=False)

        yield {
            "sqs": mock_sqs_shared,
            "idx": (mock_idx_jira, mock_idx_slack, mock_idx_generic),
        }


client = TestClient(app)


def make_jira_signature(body: bytes) -> str:
    sig = hmac.new(settings.JIRA_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def make_slack_signature(body: bytes, timestamp: str) -> str:
    sig_basestring = f"v0:{timestamp}:".encode() + body
    sig = hmac.new(settings.SLACK_SIGNING_SECRET.encode(), sig_basestring, hashlib.sha256).hexdigest()
    return f"v0={sig}"


def jira_payload(labels=None):
    return {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "id": "12345",
            "key": "CRM-123",
            "fields": {"labels": labels or ["ai-task"]},
        },
        "timestamp": int(time.time() * 1000),
    }


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "SwarmForge Ingress API" in response.json()["message"]


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_jira_valid_ai_label():
    payload = jira_payload()
    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": make_jira_signature(body),
        "Content-Type": "application/json",
    }
    response = client.post("/webhook/jira", content=body, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_jira_no_ai_label():
    payload = jira_payload(labels=["bug"])
    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": make_jira_signature(body),
        "Content-Type": "application/json",
    }
    response = client.post("/webhook/jira", content=body, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_jira_invalid_signature():
    payload = jira_payload()
    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": "sha256=invalid",
        "Content-Type": "application/json",
    }
    response = client.post("/webhook/jira", content=body, headers=headers)
    assert response.status_code == 401


def test_jira_duplicate_event(mock_deps):
    mock_deps["idx"][0].is_duplicate.return_value = True
    payload = jira_payload()
    body = json.dumps(payload).encode()
    headers = {
        "X-Hub-Signature-256": make_jira_signature(body),
        "Content-Type": "application/json",
    }
    response = client.post("/webhook/jira", content=body, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert response.json()["reason"] == "duplicate"


def test_generic_valid_token():
    headers = {"Authorization": f"Bearer {settings.GENERIC_WEBHOOK_TOKEN}"}
    response = client.post("/webhook/generic", json={"test": "data"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_generic_invalid_token():
    headers = {"Authorization": "Bearer invalid"}
    response = client.post("/webhook/generic", json={"test": "data"}, headers=headers)
    assert response.status_code == 401


# --- Security tests ---


def test_jira_payload_too_large():
    """Payloads exceeding MAX_PAYLOAD_BYTES should be rejected."""
    oversized_body = b"x" * (1_048_576 + 1)
    headers = {
        "X-Hub-Signature-256": make_jira_signature(oversized_body),
        "Content-Type": "application/json",
    }
    response = client.post("/webhook/jira", content=oversized_body, headers=headers)
    assert response.status_code == 413


def test_slack_future_timestamp_rejected():
    """Slack requests with a far-future timestamp should be rejected."""
    future_ts = str(int(time.time()) + 600)
    body = json.dumps({"type": "event_callback", "event": {"type": "app_mention", "text": "hi"}}).encode()
    sig = make_slack_signature(body, future_ts)
    headers = {
        "X-Slack-Request-Timestamp": future_ts,
        "X-Slack-Signature": sig,
        "Content-Type": "application/json",
    }
    response = client.post("/webhook/slack", content=body, headers=headers)
    assert response.status_code == 401
    assert "future" in response.json()["detail"].lower()


def test_slack_expired_timestamp_rejected():
    """Slack requests with an old timestamp should be rejected."""
    old_ts = str(int(time.time()) - 600)
    body = json.dumps({"type": "event_callback"}).encode()
    sig = make_slack_signature(body, old_ts)
    headers = {
        "X-Slack-Request-Timestamp": old_ts,
        "X-Slack-Signature": sig,
        "Content-Type": "application/json",
    }
    response = client.post("/webhook/slack", content=body, headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_slack_invalid_timestamp_format():
    """Non-numeric Slack timestamps should be rejected."""
    body = json.dumps({"type": "event_callback"}).encode()
    headers = {
        "X-Slack-Request-Timestamp": "not-a-number",
        "X-Slack-Signature": "v0=abc",
        "Content-Type": "application/json",
    }
    response = client.post("/webhook/slack", content=body, headers=headers)
    assert response.status_code == 401


def test_generic_payload_too_large():
    """Generic webhook with oversized payload should be rejected."""
    oversized_body = b"x" * (1_048_576 + 1)
    headers = {
        "Authorization": f"Bearer {settings.GENERIC_WEBHOOK_TOKEN}",
        "Content-Type": "application/json",
    }
    response = client.post("/webhook/generic", content=oversized_body, headers=headers)
    assert response.status_code == 413
