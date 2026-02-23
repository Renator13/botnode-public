from __future__ import annotations

from typing import Any, Dict, List, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KeyPointExtractorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    max_points: int = Field(default=5, ge=1, le=20)
    language: str = "en"

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("text must be non-empty")
        if len(cleaned) > 100_000:
            raise ValueError("text must be <= 100000 characters")
        return cleaned


class KeyPointExtractorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    points: List[str]


class BotNodeTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Union[str, int]
    input_data: Dict[str, Any]
