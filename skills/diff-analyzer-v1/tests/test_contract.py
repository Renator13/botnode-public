import asyncio

from diff_analyzer_v1.engine import DiffAnalyzerEngine
from diff_analyzer_v1.models import DiffAnalyzerInput


def test_detects_price_change() -> None:
    payload = DiffAnalyzerInput(content_a="Price: $10", content_b="Price: $12", focus_areas=["price"])
    output = asyncio.run(DiffAnalyzerEngine().run(payload))

    assert output.change_detected is True
    assert output.change_score > 0
    assert "Price changed" in output.summary or "price" in output.summary.lower()
