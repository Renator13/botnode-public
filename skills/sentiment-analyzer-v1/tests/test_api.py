import asyncio

import pytest
from fastapi import HTTPException

from sentiment_analyzer_v1 import api as api_module
from sentiment_analyzer_v1.models import SentimentAnalyzerInput, SentimentAnalyzerOutput


def test_internal_api_key_validation() -> None:
    api_module.INTERNAL_API_KEY = "test-key"
    api_module._validate_internal_api_key("test-key")

    with pytest.raises(HTTPException) as exc_info:
        api_module._validate_internal_api_key("wrong")
    assert exc_info.value.status_code == 401


def test_rate_limit_returns_429() -> None:
    api_module.RATE_LIMIT_MAX_REQUESTS = 2
    api_module.RATE_LIMIT_WINDOW_SECONDS = 60.0
    api_module._rate_limit_events.clear()

    asyncio.run(api_module._enforce_rate_limit())
    asyncio.run(api_module._enforce_rate_limit())

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(api_module._enforce_rate_limit())
    assert exc_info.value.status_code == 429


def test_idempotency_cache_reuses_previous_result(monkeypatch) -> None:
    api_module.IDEMPOTENCY_TTL_SECONDS = 300.0
    api_module._idempotency_cache.clear()
    calls = {"count": 0}

    async def fake_run(payload):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        return SentimentAnalyzerOutput(score=0.8, label='POSITIVE', explanation='mock')

    monkeypatch.setattr(api_module.engine, "run", fake_run)
    payload = SentimentAnalyzerInput(text='great feature')

    first = asyncio.run(api_module.run_sentiment_analyzer(payload, idempotency_key="idem-1"))
    second = asyncio.run(api_module.run_sentiment_analyzer(payload, idempotency_key="idem-1"))

    assert calls["count"] == 1
    assert first == second
