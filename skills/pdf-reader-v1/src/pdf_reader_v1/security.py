from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import httpx

MAX_DEFAULT_PDF_BYTES = 20 * 1024 * 1024


def is_safe_public_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        if hostname.lower() == "localhost":
            return False

        try:
            addr_info = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            return True

        for item in addr_info:
            ip_raw = item[4][0]
            ip = ipaddress.ip_address(ip_raw)
            if ip.is_loopback or ip.is_private or ip.is_link_local:
                return False

        return True
    except Exception:
        return False


async def fetch_pdf_with_retries(
    url: str,
    timeout_seconds: float = 20.0,
    max_attempts: int = 4,
    user_agent: str = "pdf-reader-v1/0.1",
    max_pdf_bytes: int = MAX_DEFAULT_PDF_BYTES,
) -> bytes:
    timeout = httpx.Timeout(connect=5.0, read=timeout_seconds, write=5.0, pool=5.0)
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/pdf,*/*;q=0.8",
    }

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await _request_with_retries(
            client=client,
            method="GET",
            url=url,
            headers=headers,
            max_attempts=max_attempts,
        )

    if response.status_code != 200:
        raise RuntimeError(f"pdf fetch failed: status={response.status_code}")

    _validate_response_size(response.headers, max_pdf_bytes)
    if len(response.content) > max_pdf_bytes:
        raise RuntimeError("pdf exceeds maximum allowed bytes")

    return response.content


def _validate_response_size(headers: httpx.Headers | dict, max_pdf_bytes: int) -> None:
    content_length = headers.get("content-length")
    if not content_length:
        return
    try:
        value = int(content_length)
    except ValueError:
        return
    if value > max_pdf_bytes:
        raise RuntimeError("pdf exceeds maximum allowed bytes")


async def _request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str],
    max_attempts: int = 4,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            response = await client.request(method=method, url=url, headers=headers)
            if response.status_code >= 500 and attempt < max_attempts - 1:
                await asyncio.sleep(0.35 * (2**attempt))
                continue
            return response
        except Exception as exc:
            last_exc = exc
            if attempt >= max_attempts - 1:
                break
            await asyncio.sleep(0.35 * (2**attempt))
    raise RuntimeError(f"request failed after retries: {method} {url}") from last_exc
