from __future__ import annotations

from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, field_validator


class WebScraperInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    include_html: bool = False

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("url must be non-empty")
        return cleaned


class WebScraperOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    text_content: str
    status_code: int
    html_content: Optional[str] = None


class BotNodeTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Union[str, int]
    input_data: Dict[str, Any]
