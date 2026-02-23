from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from collections import deque
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException, Request
import uvicorn

from .engine import LeadEnricherEngine
from .models import LeadEnricherInput, LeadEnricherOutput


SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8080"))
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "15"))
USER_AGENT = os.getenv("USER_AGENT", "lead-enricher-v1/0.1")
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(20 * 1024 * 1024)))
INTERNAL_API_KEY = (os.getenv("INTERNAL_API_KEY") or "").strip()
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "20"))
RATE_LIMIT_WINDOW_SECONDS = float(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "1"))
IDEMPOTENCY_TTL_SECONDS = float(os.getenv("IDEMPOTENCY_TTL_SECONDS", "300"))

app = FastAPI(title="lead_enricher_v1", version="0.1.0")
engine = LeadEnricherEngine()

_rate_limit_events: deque[float] = deque()
_rate_limit_lock = asyncio.Lock()
_idempotency_cache: dict[str, tuple[float, str, dict[str, Any]]] = {}
_idempotency_lock = asyncio.Lock()


@app.middleware("http")
async def _run_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
    if request.method.upper() == "POST" and request.url.path == "/run":
        _validate_internal_api_key(request.headers.get("X-INTERNAL-API-KEY"))
        await _enforce_rate_limit()
    return await call_next(request)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run", response_model=LeadEnricherOutput)
async def run_lead_enricher(
    payload: LeadEnricherInput,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    legacy_idempotency_key: Optional[str] = Header(default=None, alias="X-IDEMPOTENCY-KEY"),
) -> LeadEnricherOutput:
    normalized_idempotency_key = _normalize_idempotency_key(idempotency_key or legacy_idempotency_key)
    payload_fingerprint = _sha256_json(payload.model_dump(mode="json"))

    try:
        if normalized_idempotency_key:
            cached = await _get_cached_output(normalized_idempotency_key, payload_fingerprint)
            if cached is not None:
                return LeadEnricherOutput.model_validate(cached)

        output = await engine.run(payload)

        if normalized_idempotency_key:
            await _store_cached_output(
                normalized_idempotency_key,
                payload_fingerprint,
                output.model_dump(mode="json"),
            )

        return output
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _validate_internal_api_key(provided_key: Optional[str]) -> None:
    if not INTERNAL_API_KEY:
        raise HTTPException(status_code=503, detail="INTERNAL_API_KEY is not configured")
    if provided_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="invalid internal api key")


async def _enforce_rate_limit() -> None:
    if RATE_LIMIT_MAX_REQUESTS <= 0 or RATE_LIMIT_WINDOW_SECONDS <= 0:
        return

    now = time.monotonic()
    min_allowed = now - RATE_LIMIT_WINDOW_SECONDS

    async with _rate_limit_lock:
        while _rate_limit_events and _rate_limit_events[0] <= min_allowed:
            _rate_limit_events.popleft()

        if len(_rate_limit_events) >= RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(status_code=429, detail="rate limit exceeded")

        _rate_limit_events.append(now)


def _normalize_idempotency_key(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > 256:
        raise HTTPException(status_code=422, detail="idempotency key must be <= 256 characters")
    return cleaned


async def _get_cached_output(idempotency_key: str, payload_fingerprint: str) -> Optional[dict[str, Any]]:
    if IDEMPOTENCY_TTL_SECONDS <= 0:
        return None

    now = time.time()
    async with _idempotency_lock:
        _prune_idempotency_cache(now)
        cached = _idempotency_cache.get(idempotency_key)
        if cached is None:
            return None

        expires_at, cached_fingerprint, output = cached
        if expires_at <= now:
            _idempotency_cache.pop(idempotency_key, None)
            return None

        if cached_fingerprint != payload_fingerprint:
            raise HTTPException(status_code=409, detail="idempotency key reused with different payload")

        return output


async def _store_cached_output(idempotency_key: str, payload_fingerprint: str, output: dict[str, Any]) -> None:
    if IDEMPOTENCY_TTL_SECONDS <= 0:
        return

    async with _idempotency_lock:
        _prune_idempotency_cache(time.time())
        _idempotency_cache[idempotency_key] = (
            time.time() + IDEMPOTENCY_TTL_SECONDS,
            payload_fingerprint,
            output,
        )


def _prune_idempotency_cache(now: float) -> None:
    expired = [key for key, (expires_at, _, _) in _idempotency_cache.items() if expires_at <= now]
    for key in expired:
        _idempotency_cache.pop(key, None)


def _sha256_json(data: dict[str, Any]) -> str:
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    uvicorn.run("lead_enricher_v1.api:app", host=SERVICE_HOST, port=SERVICE_PORT, reload=False)


if __name__ == "__main__":
    main()
