from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotificationRouterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["email", "webhook", "slack", "discord"]
    recipient: str
    subject: Optional[str] = None
    message_body: str
    attachments: List[str] = Field(default_factory=list, max_length=20)

    @field_validator("recipient")
    @classmethod
    def _validate_recipient(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("recipient must be non-empty")
        return cleaned

    @field_validator("message_body")
    @classmethod
    def _validate_message_body(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message_body must be non-empty")
        if len(cleaned) > 20_000:
            raise ValueError("message_body must be <= 20000 characters")
        return cleaned


class NotificationRouterOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["sent", "failed", "queued"]
    provider_id: str
    timestamp: str


class BotNodeTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Union[str, int]
    input_data: Dict[str, Any]
