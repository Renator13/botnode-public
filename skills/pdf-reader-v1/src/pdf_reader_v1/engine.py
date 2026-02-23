from __future__ import annotations

import io
import os
import re

import pdfplumber

from .models import PdfReaderInput, PdfReaderOutput
from .security import fetch_pdf_with_retries, is_safe_public_http_url


class PdfReaderEngine:
    def __init__(
        self,
        timeout_seconds: float = 20.0,
        user_agent: str = "pdf-reader-v1/0.1",
        max_pdf_bytes: int = 20 * 1024 * 1024,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._max_pdf_bytes = max_pdf_bytes

    async def run(self, payload: PdfReaderInput) -> PdfReaderOutput:
        if not is_safe_public_http_url(payload.file_url):
            raise ValueError(f"url is not allowed (non-public or local): {payload.file_url}")

        pdf_bytes = await fetch_pdf_with_retries(
            url=payload.file_url,
            timeout_seconds=self._timeout_seconds,
            max_attempts=4,
            user_agent=self._user_agent,
            max_pdf_bytes=self._max_pdf_bytes,
        )

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                total_pages = len(pdf.pages)
                page_indexes = _parse_page_selection(payload.pages, total_pages)

                selected_text = []
                for idx in page_indexes:
                    text = pdf.pages[idx].extract_text() or ""
                    text = re.sub(r"\s+", " ", text).strip()
                    if text:
                        selected_text.append(text)

                metadata = {}
                for key in ("Title", "Author", "Producer", "Creator"):
                    value = (pdf.metadata or {}).get(key)
                    if value is not None:
                        metadata[key.lower()] = str(value)

                return PdfReaderOutput(
                    page_count=len(page_indexes),
                    metadata=metadata,
                    full_text="\n\n".join(selected_text),
                )
        except Exception as exc:
            raise ValueError(f"failed to parse PDF: {exc}") from exc


def _parse_page_selection(pages_expr: str | None, total_pages: int) -> list[int]:
    if total_pages <= 0:
        return []

    if not pages_expr:
        return list(range(total_pages))

    cleaned = pages_expr.strip()
    if "-" in cleaned:
        start_raw, end_raw = cleaned.split("-", 1)
        start = max(1, int(start_raw.strip()))
        end = min(total_pages, int(end_raw.strip()))
        if end < start:
            raise ValueError("invalid pages range")
        return list(range(start - 1, end))

    value = int(cleaned)
    if value < 1 or value > total_pages:
        raise ValueError("requested page is out of bounds")
    return [value - 1]
