import asyncio

from key_point_extractor_v1.engine import KeyPointExtractorEngine
from key_point_extractor_v1.models import KeyPointExtractorInput


def test_extracts_up_to_max_points() -> None:
    text = (
        "Revenue grew by 50% year over year. "
        "The company hired a new CEO in Q4. "
        "Product launch was delayed due to compliance review."
    )
    payload = KeyPointExtractorInput(text=text, max_points=2)
    output = asyncio.run(KeyPointExtractorEngine().run(payload))

    assert len(output.points) <= 2
    assert output.points
