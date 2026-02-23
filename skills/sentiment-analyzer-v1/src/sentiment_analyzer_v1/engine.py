from __future__ import annotations

import re

from .models import SentimentAnalyzerInput, SentimentAnalyzerOutput

_POSITIVE = {"love", "great", "excellent", "amazing", "good", "happy", "awesome", "fantastic"}
_NEGATIVE = {"hate", "bad", "terrible", "awful", "poor", "sad", "horrible", "worst"}


class SentimentAnalyzerEngine:
    async def run(self, payload: SentimentAnalyzerInput) -> SentimentAnalyzerOutput:
        tokens = re.findall(r"[a-z0-9']+", payload.text.lower())
        if not tokens:
            return SentimentAnalyzerOutput(score=0.0, label="NEUTRAL", explanation="No analyzable tokens were found.")

        pos = sum(1 for token in tokens if token in _POSITIVE)
        neg = sum(1 for token in tokens if token in _NEGATIVE)

        score = (pos - neg) / max(1, pos + neg)
        score = max(-1.0, min(1.0, round(score, 4)))

        if score > 0.3:
            label = "POSITIVE"
            explanation = f"Detected {pos} positive vs {neg} negative sentiment terms."
        elif score < -0.3:
            label = "NEGATIVE"
            explanation = f"Detected {neg} negative vs {pos} positive sentiment terms."
        else:
            label = "NEUTRAL"
            explanation = "Sentiment terms are balanced or sparse."

        return SentimentAnalyzerOutput(score=score, label=label, explanation=explanation)
