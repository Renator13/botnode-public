from __future__ import annotations

import csv
import io

from .models import CsvParserInput, CsvParserOutput
from .security import fetch_csv_with_retries, is_safe_public_http_url


class CsvParserEngine:
    def __init__(
        self,
        timeout_seconds: float = 20.0,
        user_agent: str = "csv-parser-v1/0.1",
        max_csv_bytes: int = 10 * 1024 * 1024,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._max_csv_bytes = max_csv_bytes

    async def run(self, payload: CsvParserInput) -> CsvParserOutput:
        if not is_safe_public_http_url(payload.file_url):
            raise ValueError(f"url is not allowed (non-public or local): {payload.file_url}")

        csv_text = await fetch_csv_with_retries(
            url=payload.file_url,
            timeout_seconds=self._timeout_seconds,
            max_attempts=4,
            user_agent=self._user_agent,
            max_csv_bytes=self._max_csv_bytes,
        )

        reader = csv.DictReader(io.StringIO(csv_text), delimiter=payload.delimiter)
        headers = list(reader.fieldnames or [])
        rows = []

        for idx, row in enumerate(reader):
            if idx >= payload.limit:
                break
            normalized = {str(key): "" if value is None else str(value) for key, value in row.items() if key is not None}
            rows.append(normalized)

        return CsvParserOutput(total_rows=len(rows), headers=headers, data=rows)
