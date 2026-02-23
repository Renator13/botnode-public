from __future__ import annotations

from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LeadEnricherInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: Optional[str] = None
    email: Optional[str] = None

    @model_validator(mode="after")
    def _validate_source(self) -> "LeadEnricherInput":
        has_domain = bool((self.domain or "").strip())
        has_email = bool((self.email or "").strip())
        if not has_domain and not has_email:
            raise ValueError("at least one of domain or email is required")

        if has_domain:
            self.domain = self.domain.strip().lower() if self.domain else self.domain
        if has_email:
            self.email = self.email.strip().lower() if self.email else self.email
        return self


class LeadEnricherOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str
    industry: str
    employees: int = Field(ge=0)
    linkedin_url: str
    source: str


class BotNodeTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Union[str, int]
    input_data: Dict[str, Any]
