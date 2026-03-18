import asyncio
import logging
import signal
from services.sqs_consumer import SQSConsumer
from services.orchestrator import orchestrator
from config import settings
from services.logging_setup import configure_logging

configure_logging("worker", settings.CLOUDWATCH_LOG_GROUP_WORKER)
logger = logging.getLogger(__name__)

async def main():
    consumer = SQSConsumer(
        queue_url=settings.SQS_QUEUE_URL,
        handler=orchestrator.handle_task
    )
    
    logger.info("SwarmForge Worker Starting...")
    
    # Handle shutdown signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(consumer.stop()))

    await consumer.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
