from __future__ import annotations

from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PdfReaderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_url: str
    pages: Optional[str] = None
    extract_tables: bool = False

    @field_validator("file_url")
    @classmethod
    def _validate_file_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("file_url must be non-empty")
        return cleaned

    @field_validator("pages")
    @classmethod
    def _validate_pages(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) > 100:
            raise ValueError("pages expression too long")
        return cleaned


class PdfReaderOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_count: int = Field(ge=0)
    metadata: Dict[str, str]
    full_text: str


class BotNodeTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Union[str, int]
    input_data: Dict[str, Any]
