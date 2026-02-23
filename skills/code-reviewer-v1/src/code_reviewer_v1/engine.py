from __future__ import annotations

from .models import CodeReviewInput, CodeReviewOutput, Issue


class CodeReviewerEngine:
    async def run(self, payload: CodeReviewInput) -> CodeReviewOutput:
        issues: list[Issue] = []

        lines = payload.code.splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Minimal deterministic checks; replace with LLM/linters later.
            if "eval(" in stripped or "exec(" in stripped:
                issues.append(
                    Issue(
                        type="security",
                        severity="high",
                        line=idx,
                        message="Potential code injection surface via dynamic execution.",
                    )
                )

            if "TODO" in stripped and payload.language in {"python", "javascript", "typescript"}:
                issues.append(
                    Issue(
                        type="maintainability",
                        severity="low",
                        line=idx,
                        message="TODO marker found; confirm backlog tracking.",
                    )
                )

        if not issues:
            summary = "No obvious issues found by the baseline static checks."
        else:
            high_count = sum(1 for issue in issues if issue.severity == "high")
            summary = f"Found {len(issues)} issue(s), including {high_count} high-severity finding(s)."

        return CodeReviewOutput(issues=issues, summary=summary)
