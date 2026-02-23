import asyncio

from lead_enricher_v1.engine import LeadEnricherEngine
from lead_enricher_v1.models import LeadEnricherInput


def test_contract_returns_mock_record_for_known_domain() -> None:
    payload = LeadEnricherInput(domain="stripe.com")
    output = asyncio.run(LeadEnricherEngine().run(payload))

    assert output.company_name == "Stripe"
    assert output.source == "mock_db"
