import asyncio

import httpx

from code_reviewer_v1.worker import _compute_contextual_proof_hash, _request_with_retries


def test_proof_hash_binds_context() -> None:
    base = _compute_contextual_proof_hash("task-1", "code_reviewer_v1", {"a": 1}, {"x": 1})
    changed_input = _compute_contextual_proof_hash("task-1", "code_reviewer_v1", {"a": 2}, {"x": 1})
    changed_task = _compute_contextual_proof_hash("task-2", "code_reviewer_v1", {"a": 1}, {"x": 1})
    changed_output = _compute_contextual_proof_hash("task-1", "code_reviewer_v1", {"a": 1}, {"x": 2})

    assert base != changed_input
    assert base != changed_task
    assert base != changed_output


def test_request_with_retries_uses_exponential_backoff(monkeypatch) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("code_reviewer_v1.worker.asyncio.sleep", fake_sleep)

    class FakeClient:
        def __init__(self) -> None:
            self.attempt = 0

        async def request(self, **kwargs):  # type: ignore[no-untyped-def]
            self.attempt += 1
            if self.attempt <= 2:
                raise httpx.ReadTimeout("timeout")
            req = httpx.Request("GET", "https://example.com")
            return httpx.Response(200, request=req)

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
