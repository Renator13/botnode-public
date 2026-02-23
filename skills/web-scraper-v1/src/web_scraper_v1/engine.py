from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .models import WebScraperInput, WebScraperOutput
from .security import fetch_with_retries, is_safe_public_http_url


class WebScraperEngine:
    def __init__(self, timeout_seconds: float = 15.0, user_agent: str = "web-scraper-v1/0.1") -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent

    async def run(self, payload: WebScraperInput) -> WebScraperOutput:
        if not is_safe_public_http_url(payload.url):
            raise ValueError(f"url is not allowed (non-public or local): {payload.url}")

        response = await fetch_with_retries(
            url=payload.url,
            timeout_seconds=self._timeout_seconds,
            max_attempts=4,
            user_agent=self._user_agent,
        )

        title, text = _parse_html(response.text)

        return WebScraperOutput(
            title=title,
            text_content=text,
            status_code=response.status_code,
            html_content=response.text if payload.include_html else None,
        )


def _parse_html(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    for tag_name in ("script", "style", "noscript", "nav", "footer"):
        for element in soup.find_all(tag_name):
            element.decompose()

    title = (soup.title.string or "").strip() if soup.title else ""
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return title, text
