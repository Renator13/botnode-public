import asyncio

import httpx

from key_point_extractor_v1.worker import _build_idempotency_key, _compute_contextual_proof_hash, _request_with_retries


def test_proof_hash_binds_context() -> None:
    base = _compute_contextual_proof_hash("task-1", "key_point_extractor_v1", {"a": 1}, {"x": 1})
    changed_input = _compute_contextual_proof_hash("task-1", "key_point_extractor_v1", {"a": 2}, {"x": 1})
    changed_output = _compute_contextual_proof_hash("task-1", "key_point_extractor_v1", {"a": 1}, {"x": 2})

    assert base != changed_input
    assert base != changed_output


def test_idempotency_key_is_deterministic_and_bound_to_input() -> None:
    base = _build_idempotency_key("task-1", "key_point_extractor_v1", {"a": 1})
    same = _build_idempotency_key("task-1", "key_point_extractor_v1", {"a": 1})
    changed = _build_idempotency_key("task-1", "key_point_extractor_v1", {"a": 2})

    assert base == same
    assert base != changed


def test_request_with_retries_uses_exponential_backoff(monkeypatch) -> None:
    sleeps = []

    async def fake_sleep(seconds):  # type: ignore[no-untyped-def]
        sleeps.append(seconds)

    monkeypatch.setattr("key_point_extractor_v1.worker.asyncio.sleep", fake_sleep)

    class FakeClient:
        def __init__(self):
            self.attempt = 0

        async def request(self, **kwargs):  # type: ignore[no-untyped-def]
            self.attempt += 1
            if self.attempt <= 2:
                raise httpx.ReadTimeout("timeout")
            return httpx.Response(200, request=httpx.Request("GET", "https://example.com"))

    async def run_test() -> None:
        response = await _request_with_retries(
            client=FakeClient(),  # type: ignore[arg-type]
            method="GET",
            url="https://example.com",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200

    asyncio.run(run_test())
    assert sleeps == [0.35, 0.7]
