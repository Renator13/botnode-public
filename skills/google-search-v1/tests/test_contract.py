import asyncio

from google_search_v1.engine import GoogleSearchEngine
from google_search_v1.models import GoogleSearchInput


def test_contract_returns_requested_number_of_results() -> None:
    payload = GoogleSearchInput(query="botnode competitors", num_results=3)
    output = asyncio.run(GoogleSearchEngine().run(payload))

    assert len(output.results) == 3
    assert output.results[0].title
