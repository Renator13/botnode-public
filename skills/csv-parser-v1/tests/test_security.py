import asyncio

import httpx
import pytest

from csv_parser_v1.security import _request_with_retries, _validate_response_size, is_safe_public_http_url


def test_blocks_ssrf_vectors() -> None:
    assert is_safe_public_http_url("http://127.0.0.1/") is False
    assert is_safe_public_http_url("http://localhost/") is False
    assert is_safe_public_http_url("http://10.0.0.1/") is False
    assert is_safe_public_http_url("http://192.168.1.1/") is False
    assert is_safe_public_http_url("https://example.com/") is True


def test_request_with_retries_uses_exponential_backoff(monkeypatch) -> None:
    sleeps = []

    async def fake_sleep(seconds):  # type: ignore[no-untyped-def]
        sleeps.append(seconds)

    monkeypatch.setattr("csv_parser_v1.security.asyncio.sleep", fake_sleep)

    class FakeClient:
        def __init__(self):
            self.attempt = 0

        async def request(self, **kwargs):  # type: ignore[no-untyped-def]
            self.attempt += 1
            if self.attempt <= 2:
                raise httpx.ReadTimeout("timeout")
            return httpx.Response(200, request=httpx.Request("GET", "https://example.com"), text="a,b\n1,2")

    async def run_test() -> None:
        response = await _request_with_retries(
            client=FakeClient(),  # type: ignore[arg-type]
            method="GET",
            url="https://example.com",
            headers={"Accept": "text/csv"},
        )
        assert response.status_code == 200

    asyncio.run(run_test())
    assert sleeps == [0.35, 0.7]


def test_rejects_oversized_content_length_header() -> None:
    with pytest.raises(RuntimeError):
        _validate_response_size({"content-length": str((10 * 1024 * 1024) + 1)}, 10 * 1024 * 1024)
