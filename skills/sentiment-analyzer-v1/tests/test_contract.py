import asyncio

from sentiment_analyzer_v1.engine import SentimentAnalyzerEngine
from sentiment_analyzer_v1.models import SentimentAnalyzerInput


def test_positive_text_maps_to_positive_label() -> None:
    payload = SentimentAnalyzerInput(text="I love this great feature")
    output = asyncio.run(SentimentAnalyzerEngine().run(payload))

    assert output.label == "POSITIVE"
    assert output.score > 0
