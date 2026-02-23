from __future__ import annotations

from typing import Any, Dict, List, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CsvParserInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_url: str
    delimiter: str = ","
    limit: int = Field(default=100, ge=1, le=5000)

    @field_validator("file_url")
    @classmethod
    def _validate_file_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("file_url must be non-empty")
        return cleaned

    @field_validator("delimiter")
    @classmethod
    def _validate_delimiter(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) != 1:
            raise ValueError("delimiter must be a single character")
        return cleaned


class CsvParserOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_rows: int = Field(ge=0)
    headers: List[str]
    data: List[Dict[str, str]]


class BotNodeTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Union[str, int]
    input_data: Dict[str, Any]
