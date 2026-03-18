import logging

from botocore.exceptions import BotoCoreError, ClientError
from config import settings
from models.sqs_message import SQSMessageEnvelope
from services.aws_session import get_aws_client

logger = logging.getLogger(__name__)


class SQSProducer:
    def __init__(self) -> None:
        self.sqs = get_aws_client("sqs")
        self.queue_url = settings.SQS_QUEUE_URL

    async def publish(self, envelope: SQSMessageEnvelope) -> bool:
        """Publishes a task payload to SQS."""
        try:
            message_body = envelope.model_dump_json()

            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message_body,
                MessageAttributes={
                    "TaskId": {"StringValue": envelope.task_id, "DataType": "String"},
                    "Source": {"StringValue": envelope.source, "DataType": "String"},
                    "EventType": {"StringValue": envelope.event_type, "DataType": "String"},
                },
            )
            return "MessageId" in response
        except ClientError as exc:
            logger.error("Failed to publish to SQS: %s", exc)
            return False
        except BotoCoreError as exc:
            logger.error("SQS infrastructure error during publish: %s", exc)
            return False


# Singleton instance
sqs_producer = SQSProducer()
