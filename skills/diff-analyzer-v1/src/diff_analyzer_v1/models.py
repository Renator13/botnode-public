from __future__ import annotations

from typing import Any, Dict, List, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DiffAnalyzerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_a: str
    content_b: str
    focus_areas: List[str] = Field(default_factory=list, max_length=20)

    @field_validator("content_a", "content_b")
    @classmethod
    def _validate_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content fields must be non-empty")
        if len(cleaned) > 200_000:
            raise ValueError("content must be <= 200000 characters")
        return cleaned


class DiffAnalyzerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    change_detected: bool
    change_score: float = Field(ge=0.0, le=1.0)
    summary: str
    diff_snippet: str


class BotNodeTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Union[str, int]
    input_data: Dict[str, Any]
