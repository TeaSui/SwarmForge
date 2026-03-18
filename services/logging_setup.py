from __future__ import annotations

import json
import logging
import os
import socket
from contextvars import ContextVar
from datetime import UTC, datetime

from config import settings
from services.aws_session import get_boto3_session

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def set_correlation_id(correlation_id: str) -> None:
    _correlation_id.set(correlation_id or "-")


def clear_correlation_id() -> None:
    _correlation_id.set("-")


class JsonLogFormatter(logging.Formatter):
    def __init__(self, component: str):
        super().__init__()
        self.component = component

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "component": self.component,
            "correlation_id": _correlation_id.get(),
            "event": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(service_name: str, log_group_name: str) -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_swarmforge_configured", False):
        return

    level = getattr(logging, settings.CLOUDWATCH_LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(level)

    formatter = JsonLogFormatter(component=service_name)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    if settings.CLOUDWATCH_ENABLED:
        try:
            import watchtower  # type: ignore

            session = get_boto3_session()
            cloudwatch_handler = watchtower.CloudWatchLogHandler(
                boto3_client=session.client("logs"),
                log_group_name=log_group_name,
                stream_name=f"{service_name}-{socket.gethostname()}-{os.getpid()}",
                create_log_group=True,
            )
            cloudwatch_handler.setFormatter(formatter)
            root_logger.addHandler(cloudwatch_handler)
            root_logger.info(
                "CloudWatch logging enabled for %s -> %s",
                service_name,
                log_group_name,
            )
        except Exception:
            root_logger.exception("Failed to initialize CloudWatch logging")

    root_logger._swarmforge_configured = True
