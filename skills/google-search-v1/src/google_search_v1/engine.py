from __future__ import annotations

import asyncio
import os
from typing import List

import httpx

from .models import GoogleSearchInput, GoogleSearchOutput, SearchResultItem


class GoogleSearchEngine:
    def __init__(self) -> None:
        self._provider = (os.getenv("SEARCH_PROVIDER") or "mock").strip().lower()
        self._serper_api_key = (os.getenv("SERPER_API_KEY") or "").strip()
        self._serper_endpoint = (os.getenv("SERPER_ENDPOINT") or "https://google.serper.dev/search").strip()
        self._timeout_seconds = float(os.getenv("HTTP_TIMEOUT_SECONDS", "15"))
        self._user_agent = (os.getenv("USER_AGENT") or "google-search-v1/0.1").strip()

    async def run(self, payload: GoogleSearchInput) -> GoogleSearchOutput:
        if self._provider == "serper" and self._serper_api_key:
            items = await self._search_serper(payload.query, payload.num_results)
            return GoogleSearchOutput(results=items)

        return GoogleSearchOutput(results=_mock_results(payload.query, payload.num_results))

    async def _search_serper(self, query: str, num_results: int) -> List[SearchResultItem]:
        timeout = httpx.Timeout(connect=5.0, read=self._timeout_seconds, write=5.0, pool=5.0)
        headers = {
            "X-API-KEY": self._serper_api_key,
            "Content-Type": "application/json",
            "User-Agent": self._user_agent,
        }

        payload = {"q": query, "num": num_results}
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await _request_with_retries(
                client=client,
                method="POST",
                url=self._serper_endpoint,
                headers=headers,
                json_payload=payload,
            )

        if response.status_code != 200:
            return _mock_results(query, num_results)

        body = response.json()
        organic = body.get("organic") if isinstance(body, dict) else None
        if not isinstance(organic, list):
            return _mock_results(query, num_results)

        results: List[SearchResultItem] = []
        for item in organic:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            link = str(item.get("link") or "").strip()
            snippet = str(item.get("snippet") or "").strip()
            if not (title and link):
                continue
            results.append(SearchResultItem(title=title, link=link, snippet=snippet))
            if len(results) >= num_results:
                break

        return results or _mock_results(query, num_results)


async def _request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str],
    json_payload: dict | None = None,
    max_attempts: int = 4,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            response = await client.request(method=method, url=url, headers=headers, json=json_payload)
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


def _mock_results(query: str, num_results: int) -> List[SearchResultItem]:
    return [
        SearchResultItem(
            title=f"Mock result {i + 1} for {query}",
            link=f"https://example.com/search/{i + 1}",
            snippet=f"Synthetic snippet {i + 1} for query '{query}'.",
        )
        for i in range(num_results)
    ]
