from __future__ import annotations

import re

from .models import KeyPointExtractorInput, KeyPointExtractorOutput


class KeyPointExtractorEngine:
    async def run(self, payload: KeyPointExtractorInput) -> KeyPointExtractorOutput:
        sentences = re.split(r"(?<=[.!?])\s+", payload.text.strip())

        candidates = [s.strip() for s in sentences if len(s.strip()) >= 30]
        if not candidates:
            compact = payload.text.strip()
            return KeyPointExtractorOutput(points=[compact[:240]])

        candidates.sort(key=lambda item: (len(item), item), reverse=True)

        points = []
        seen = set()
        for sentence in candidates:
            normalized = sentence.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            points.append(sentence[:240])
            if len(points) >= payload.max_points:
                break

        return KeyPointExtractorOutput(points=points)
