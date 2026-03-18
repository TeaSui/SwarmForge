from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from uuid import uuid4
from datetime import datetime, UTC

class SQSMessageEnvelope(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
