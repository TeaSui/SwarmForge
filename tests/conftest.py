from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def pytest_sessionstart(session):  # type: ignore[no-untyped-def]
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("AWS_PROFILE", "ai-driven")
    os.environ.setdefault("AWS_REGION", "ap-southeast-1")
    os.environ.setdefault(
        "SQS_QUEUE_URL",
        "https://sqs.ap-southeast-1.amazonaws.com/123456789012/swarmforge-tasks",
    )
    os.environ.setdefault("DYNAMODB_IDEMPOTENCY_TABLE", "swarmforge-idempotency")
    os.environ.setdefault("JIRA_WEBHOOK_SECRET", "test-jira-secret")
    os.environ.setdefault("SLACK_SIGNING_SECRET", "test-slack-secret")
    os.environ.setdefault("GENERIC_WEBHOOK_TOKEN", "test-generic-token")


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB resource for unit tests."""
    with patch("services.aws_session.get_boto3_session") as mock_session:
        mock_resource = MagicMock()
        mock_table = MagicMock()
        mock_resource.Table.return_value = mock_table
        mock_session.return_value.resource.return_value = mock_resource
        mock_session.return_value.client.return_value = MagicMock()
        yield {"session": mock_session, "resource": mock_resource, "table": mock_table}


@pytest.fixture
def mock_sqs():
    """Mock SQS client for unit tests."""
    with patch("services.aws_session.get_boto3_session") as mock_session:
        mock_client = MagicMock()
        mock_client.send_message.return_value = {"MessageId": "test-message-id"}
        mock_client.receive_message.return_value = {"Messages": []}
        mock_session.return_value.client.return_value = mock_client
        yield {"session": mock_session, "client": mock_client}


@pytest.fixture
def sample_jira_envelope():
    """Sample Jira SQS message envelope."""
    return {
        "task_id": "SCRUM-42",
        "source": "jira",
        "event_type": "jira:issue_updated",
        "payload": {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "id": "10042",
                "key": "SCRUM-42",
                "fields": {
                    "summary": "Implement auth module",
                    "labels": ["ai-task"],
                    "description": None,
                },
            },
        },
        "timestamp": "2026-03-10T00:00:00+00:00",
        "metadata": {"correlation_id": "test-corr-id"},
    }


@pytest.fixture
def sample_slack_envelope():
    """Sample Slack SQS message envelope."""
    return {
        "task_id": "slack-evt-001",
        "source": "slack",
        "event_type": "app_mention",
        "payload": {
            "type": "event_callback",
            "event_id": "Ev123",
            "event": {
                "type": "app_mention",
                "text": "@ai please fix the login bug",
                "ts": "1710000000.000100",
            },
        },
        "timestamp": "2026-03-10T00:00:00+00:00",
        "metadata": {"correlation_id": "test-corr-id"},
    }


@pytest.fixture
def mock_budget_manager():
    """Mock BudgetManager for unit tests."""
    manager = MagicMock()
    manager.current_tokens = 0
    manager.current_usd = 0.0
    manager.add_usage = AsyncMock()
    manager.persist_usage = AsyncMock()
    manager.reset = AsyncMock()
    return manager


@pytest.fixture
def fastapi_test_client():
    """FastAPI test client with mocked dependencies."""
    from httpx import ASGITransport, AsyncClient

    from main import app

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")
