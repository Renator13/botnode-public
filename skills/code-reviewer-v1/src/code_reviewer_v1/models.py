from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_CODE_LENGTH = 20_000


class CodeReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str
    code: str
    context: Optional[str] = None

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("language must be non-empty")
        return cleaned

    @field_validator("code")
    @classmethod
    def _validate_code(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("code must be non-empty")
        if len(cleaned) > MAX_CODE_LENGTH:
            raise ValueError(f"code must be <= {MAX_CODE_LENGTH} characters")
        return value


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    severity: str
    line: int = Field(default=0, ge=0)
    message: str


class CodeReviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: List[Issue]
    summary: str


class BotNodeTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Union[str, int]
    input_data: Dict[str, Any]
