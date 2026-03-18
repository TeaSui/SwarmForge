from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from services.deduplication import DynamoDBDeduplicator


@pytest.fixture
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")


@pytest.fixture
def dynamo_table(aws_credentials):
    with mock_aws():
        client = boto3.client("dynamodb", region_name="ap-southeast-1")
        client.create_table(
            TableName="swarmforge-idempotency",
            KeySchema=[{"AttributeName": "idempotency_key", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "idempotency_key", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield "swarmforge-idempotency"


def test_first_event_is_new(dynamo_table):
    dedup = DynamoDBDeduplicator(table_name=dynamo_table, region="ap-southeast-1")
    assert dedup.is_new_event("key-abc-123") is True


def test_second_event_is_duplicate(dynamo_table):
    dedup = DynamoDBDeduplicator(table_name=dynamo_table, region="ap-southeast-1")
    assert dedup.is_new_event("key-xyz-456") is True
    assert dedup.is_new_event("key-xyz-456") is False


def test_different_keys_both_new(dynamo_table):
    dedup = DynamoDBDeduplicator(table_name=dynamo_table, region="ap-southeast-1")
    assert dedup.is_new_event("key-alpha") is True
    assert dedup.is_new_event("key-beta") is True
