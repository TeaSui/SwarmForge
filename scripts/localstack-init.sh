#!/bin/bash
set -e

REGION="ap-southeast-1"

echo "Creating SQS queue..."
awslocal sqs create-queue --queue-name swarmforge-events --region "$REGION"

echo "Creating DynamoDB tables..."
awslocal dynamodb create-table \
  --table-name swarmforge-idempotency \
  --attribute-definitions AttributeName=dedupe_key,AttributeType=S \
  --key-schema AttributeName=dedupe_key,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION"

awslocal dynamodb create-table \
  --table-name swarmforge-tasks \
  --attribute-definitions AttributeName=task_id,AttributeType=S \
  --key-schema AttributeName=task_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION"

awslocal dynamodb create-table \
  --table-name swarmforge-budget \
  --attribute-definitions AttributeName=task_id,AttributeType=S \
  --key-schema AttributeName=task_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION"

echo "LocalStack init complete."
echo "SQS Queue URL: http://localhost:4566/000000000000/swarmforge-events"
