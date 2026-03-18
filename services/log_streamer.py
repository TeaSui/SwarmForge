import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class LogStreamer:
    """
    Emits task-scoped progress logs.
    """
    def __init__(self):
        self.is_active = True

    async def stream_log(self, task_id: str, message: str, level: str = "INFO"):
        """
        Streams a log entry for a specific task.
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "level": level,
            "message": message
        }
        
        logger.log(getattr(logging, level.upper(), logging.INFO), "task_id=%s %s", task_id, message)
        # await self._broadcast(log_entry)

    async def _broadcast(self, entry: Dict[str, Any]):
        # Future: broadcast to connected WebSocket clients
        pass

log_streamer = LogStreamer()
