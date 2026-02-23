import asyncio

import httpx

from notification_router_v1.security import _request_with_retries, is_safe_public_http_url


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

    monkeypatch.setattr("notification_router_v1.security.asyncio.sleep", fake_sleep)

    class FakeClient:
        def __init__(self):
            self.attempt = 0

        async def request(self, **kwargs):  # type: ignore[no-untyped-def]
            self.attempt += 1
            if self.attempt <= 2:
                raise httpx.ReadTimeout("timeout")
            return httpx.Response(204, request=httpx.Request("POST", "https://example.com"))

    async def run_test() -> None:
        response = await _request_with_retries(
            client=FakeClient(),  # type: ignore[arg-type]
            method="POST",
            url="https://example.com",
            headers={"Content-Type": "application/json"},
            json_payload={"x": 1},
        )
        assert response.status_code == 204

    asyncio.run(run_test())
    assert sleeps == [0.35, 0.7]
