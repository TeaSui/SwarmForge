import re
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class JiraIssueFields(BaseModel):
    labels: List[str] = []
    summary: Optional[str] = None
    description: Optional[str] = None


class JiraIssue(BaseModel):
    id: str
    key: str
    fields: JiraIssueFields

    @field_validator("key", mode="before")
    @classmethod
    def validate_key(cls, value: str) -> str:
        if not re.match(r"^[A-Z]+-\d+$", str(value)):
            raise ValueError(f"Invalid Jira issue key format: {value}")
        return value


class JiraWebhookPayload(BaseModel):
    webhookEvent: str
    issue: Optional[JiraIssue] = None
    timestamp: Optional[int] = None

    @field_validator("webhookEvent", mode="before")
    @classmethod
    def validate_webhook_event(cls, value: str) -> str:
        if not str(value).strip():
            raise ValueError("webhookEvent must not be empty")
        return value


class SlackEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    text: Optional[str] = None
    ts: Optional[str] = None


class SlackWebhookPayload(BaseModel):
    type: str
    event_id: Optional[str] = None
    event: Optional[SlackEvent] = None
    token: Optional[str] = None
    challenge: Optional[str] = None


class GenericWebhookPayload(BaseModel):
    id: Optional[str] = None
    event_type: Optional[str] = None
    data: Optional[dict[str, Any]] = None
