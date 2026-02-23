from __future__ import annotations

from typing import Any, Dict, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SentimentAnalyzerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("text must be non-empty")
        if len(cleaned) > 20_000:
            raise ValueError("text must be <= 20000 characters")
        return cleaned


class SentimentAnalyzerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=-1.0, le=1.0)
    label: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]
    explanation: str


class BotNodeTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Union[str, int]
    input_data: Dict[str, Any]
