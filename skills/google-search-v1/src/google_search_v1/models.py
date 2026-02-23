from __future__ import annotations

from typing import Any, Dict, List, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GoogleSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    num_results: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must be non-empty")
        if len(cleaned) > 512:
            raise ValueError("query must be <= 512 characters")
        return cleaned


class SearchResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    link: str
    snippet: str


class GoogleSearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: List[SearchResultItem]


class BotNodeTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Union[str, int]
    input_data: Dict[str, Any]
