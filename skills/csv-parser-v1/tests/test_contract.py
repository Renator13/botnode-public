import asyncio

from csv_parser_v1.engine import CsvParserEngine
from csv_parser_v1.models import CsvParserInput


def test_parses_csv_rows(monkeypatch) -> None:
    async def fake_fetch_csv_with_retries(**kwargs):  # type: ignore[no-untyped-def]
        return "email,name\na@example.com,Alice\nb@example.com,Bob\n"

    monkeypatch.setattr("csv_parser_v1.engine.fetch_csv_with_retries", fake_fetch_csv_with_retries)

    payload = CsvParserInput(file_url="https://example.com/data.csv", limit=1)
    output = asyncio.run(CsvParserEngine().run(payload))

    assert output.total_rows == 1
    assert output.headers == ["email", "name"]
