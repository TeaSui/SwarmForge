import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from services.idempotency import IdempotencyStore


@pytest.mark.asyncio
async def test_is_duplicate_new_key():
    with patch("services.idempotency.get_boto3_session") as mock_get_session:
        mock_session = MagicMock()
        mock_dynamo = MagicMock()
        mock_session.client.return_value = mock_dynamo
        mock_get_session.return_value = mock_session
        mock_dynamo.put_item.return_value = {}

        service = IdempotencyStore(
            table_name="swarmforge-idempotency",
            region="ap-southeast-1",
        )
        is_dup = await service.is_duplicate("new_key")

        assert is_dup is False
        mock_dynamo.put_item.assert_called_once()


@pytest.mark.asyncio
async def test_is_duplicate_existing_key():
    with patch("services.idempotency.get_boto3_session") as mock_get_session:
        mock_session = MagicMock()
        mock_dynamo = MagicMock()
        mock_session.client.return_value = mock_dynamo
        mock_get_session.return_value = mock_session
        error_response = {"Error": {"Code": "ConditionalCheckFailedException"}}
        mock_dynamo.put_item.side_effect = ClientError(error_response, "PutItem")

        service = IdempotencyStore(
            table_name="swarmforge-idempotency",
            region="ap-southeast-1",
        )
        is_dup = await service.is_duplicate("existing_key")

        assert is_dup is True


@pytest.mark.asyncio
async def test_sync_is_new_event():
    with patch("services.idempotency.get_boto3_session") as mock_get_session:
        mock_session = MagicMock()
        mock_dynamo = MagicMock()
        mock_session.client.return_value = mock_dynamo
        mock_get_session.return_value = mock_session
        mock_dynamo.put_item.return_value = {}

        service = IdempotencyStore(
            table_name="swarmforge-idempotency",
            region="ap-southeast-1",
        )
        assert service.is_new_event("sync_key") is True
