from __future__ import annotations

from .models import LeadEnricherInput, LeadEnricherOutput


_MOCK_BY_DOMAIN = {
    "stripe.com": {
        "company_name": "Stripe",
        "industry": "Fintech",
        "employees": 5000,
        "linkedin_url": "https://linkedin.com/company/stripe",
        "source": "mock_db",
    },
    "openai.com": {
        "company_name": "OpenAI",
        "industry": "AI",
        "employees": 2000,
        "linkedin_url": "https://linkedin.com/company/openai",
        "source": "mock_db",
    },
}


class LeadEnricherEngine:
    async def run(self, payload: LeadEnricherInput) -> LeadEnricherOutput:
        domain = payload.domain or _domain_from_email(payload.email)

        if domain and domain in _MOCK_BY_DOMAIN:
            return LeadEnricherOutput(**_MOCK_BY_DOMAIN[domain])

        company_name = domain.split(".")[0].title() if domain else "Unknown"
        return LeadEnricherOutput(
            company_name=company_name,
            industry="Unknown",
            employees=0,
            linkedin_url="",
            source="not_found",
        )


def _domain_from_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return email.split("@", 1)[1].lower().strip()
