from __future__ import annotations

import difflib
import re

from .models import DiffAnalyzerInput, DiffAnalyzerOutput


class DiffAnalyzerEngine:
    async def run(self, payload: DiffAnalyzerInput) -> DiffAnalyzerOutput:
        ratio = difflib.SequenceMatcher(a=payload.content_a, b=payload.content_b).ratio()
        change_detected = ratio < 0.9999
        change_score = max(0.0, min(1.0, round(1.0 - ratio, 4)))

        diff_lines = list(
            difflib.unified_diff(
                payload.content_a.splitlines(),
                payload.content_b.splitlines(),
                fromfile="content_a",
                tofile="content_b",
                lineterm="",
                n=2,
            )
        )
        diff_snippet = "\n".join(diff_lines[:40])

        summary = _build_summary(payload.content_a, payload.content_b, payload.focus_areas, change_detected)

        return DiffAnalyzerOutput(
            change_detected=change_detected,
            change_score=change_score,
            summary=summary,
            diff_snippet=diff_snippet,
        )


def _build_summary(content_a: str, content_b: str, focus_areas: list[str], change_detected: bool) -> str:
    if not change_detected:
        return "No meaningful difference was detected between the two inputs."

    for area in focus_areas:
        area_lower = area.lower().strip()
        if not area_lower:
            continue

        old_mentions = len(re.findall(re.escape(area_lower), content_a.lower()))
        new_mentions = len(re.findall(re.escape(area_lower), content_b.lower()))
        if old_mentions != new_mentions:
            return f"Detected changes around focus area '{area}': occurrences changed from {old_mentions} to {new_mentions}."

    price_a = _extract_first_price(content_a)
    price_b = _extract_first_price(content_b)
    if price_a is not None and price_b is not None and price_a != price_b:
        pct = ((price_b - price_a) / price_a * 100.0) if price_a != 0 else 0.0
        return f"Price changed from ${price_a:g} to ${price_b:g} ({pct:+.2f}%)."

    return "Content changed semantically; review diff_snippet for exact line-level changes."


def _extract_first_price(content: str) -> float | None:
    match = re.search(r"\$(\d+(?:\.\d+)?)", content)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None
