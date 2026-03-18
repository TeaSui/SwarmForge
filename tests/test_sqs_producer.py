import pytest
import json
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from models.sqs_message import SQSMessageEnvelope
from services.sqs_producer import SQSProducer

@pytest.mark.asyncio
async def test_sqs_producer_publish_success():
    with patch("services.sqs_producer.get_boto3_session") as mock_get_session:
        mock_session = MagicMock()
        mock_sqs = MagicMock()
        mock_session.client.return_value = mock_sqs
        mock_get_session.return_value = mock_session
        mock_sqs.send_message.return_value = {"MessageId": "msg-123"}
        
        producer = SQSProducer()
        envelope = SQSMessageEnvelope(
            source="test",
            event_type="test_event",
            payload={"foo": "bar"}
        )
        
        success = await producer.publish(envelope)
        
        assert success is True
        mock_sqs.send_message.assert_called_once()
        args, kwargs = mock_sqs.send_message.call_args
        body = json.loads(kwargs["MessageBody"])
        assert body["source"] == "test"
        assert body["payload"]["foo"] == "bar"

@pytest.mark.asyncio
async def test_sqs_producer_publish_failure():
    with patch("services.sqs_producer.get_boto3_session") as mock_get_session:
        mock_session = MagicMock()
        mock_sqs = MagicMock()
        mock_session.client.return_value = mock_sqs
        mock_get_session.return_value = mock_session
        mock_sqs.send_message.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable", "Message": "SQS Error"}},
            "SendMessage",
        )
        
        producer = SQSProducer()
        envelope = SQSMessageEnvelope(
            source="test",
            event_type="test_event",
            payload={"foo": "bar"}
        )
        
        success = await producer.publish(envelope)
        assert success is False
