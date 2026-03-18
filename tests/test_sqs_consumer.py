import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from services.sqs_consumer import SQSConsumer


@pytest.mark.asyncio
async def test_sqs_consumer_process_message_success():
    mock_handler = AsyncMock()
    with patch("services.sqs_consumer.get_boto3_session") as mock_get_session:
        mock_session = MagicMock()
        mock_sqs = MagicMock()
        mock_session.client.return_value = mock_sqs
        mock_get_session.return_value = mock_session
        consumer = SQSConsumer("test-url", mock_handler)

        message = {
            "ReceiptHandle": "rh-123",
            "Body": json.dumps({"task_id": "task-abc", "payload": {"foo": "bar"}}),
        }

        await consumer._process_message(message)

        mock_handler.assert_called_once()
        mock_sqs.delete_message.assert_called_once_with(
            QueueUrl="test-url",
            ReceiptHandle="rh-123",
        )


@pytest.mark.asyncio
async def test_sqs_consumer_process_message_fail_no_delete():
    mock_handler = AsyncMock(side_effect=Exception("Handler failed"))
    with patch("services.sqs_consumer.get_boto3_session") as mock_get_session:
        mock_session = MagicMock()
        mock_sqs = MagicMock()
        mock_session.client.return_value = mock_sqs
        mock_get_session.return_value = mock_session
        consumer = SQSConsumer("test-url", mock_handler)

        message = {
            "ReceiptHandle": "rh-123",
            "Body": json.dumps({"test": "data"}),
        }

        await consumer._process_message(message)

        mock_handler.assert_called_once()
        mock_sqs.delete_message.assert_not_called()


@pytest.mark.asyncio
async def test_sqs_consumer_malformed_json():
    mock_handler = AsyncMock()
    with patch("services.sqs_consumer.get_boto3_session") as mock_get_session:
        mock_session = MagicMock()
        mock_sqs = MagicMock()
        mock_session.client.return_value = mock_sqs
        mock_get_session.return_value = mock_session
        consumer = SQSConsumer("test-url", mock_handler)

        message = {
            "ReceiptHandle": "rh-456",
            "Body": "not-valid-json{{{",
            "MessageId": "msg-456",
        }

        await consumer._process_message(message)

        mock_handler.assert_not_called()
        mock_sqs.delete_message.assert_not_called()


def test_backoff_delay_increases():
    with patch("services.sqs_consumer.get_boto3_session") as mock_get_session:
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_get_session.return_value = mock_session
        consumer = SQSConsumer("test-url", AsyncMock())

        delay_1 = consumer._backoff_delay(1)
        delay_3 = consumer._backoff_delay(3)

        assert delay_1 < delay_3
        assert delay_1 >= 1.0
