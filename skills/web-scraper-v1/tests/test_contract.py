import asyncio

from web_scraper_v1.engine import WebScraperEngine
from web_scraper_v1.models import WebScraperInput


def test_contract_extracts_text_and_title(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200
        text = "<html><head><title>Post</title></head><body><p>Hello world</p></body></html>"

    async def fake_fetch_with_retries(**kwargs):  # type: ignore[no-untyped-def]
        return FakeResponse()

    monkeypatch.setattr("web_scraper_v1.engine.fetch_with_retries", fake_fetch_with_retries)

    payload = WebScraperInput(url="https://example.com/post")
    output = asyncio.run(WebScraperEngine().run(payload))

    assert output.title == "Post"
    assert "Hello world" in output.text_content
