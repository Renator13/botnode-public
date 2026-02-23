from __future__ import annotations

from typing import Any, Dict, Literal, Union

from pydantic import BaseModel, ConfigDict, field_validator


class SchedulerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cron_expression: str
    target_node_id: str
    task_payload: Dict[str, Any]
    timezone: str = "UTC"

    @field_validator("cron_expression", "target_node_id", "timezone")
    @classmethod
    def _validate_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("string fields must be non-empty")
        return cleaned


class SchedulerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: Literal["scheduled"]
    next_run: str


class BotNodeTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Union[str, int]
    input_data: Dict[str, Any]
