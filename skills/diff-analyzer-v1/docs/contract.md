# Contract: diff_analyzer_v1

## Objective
Compare two text inputs and identify semantic changes.

## Input
```json
{
  "content_a": "Price: $10",
  "content_b": "Price: $12",
  "focus_areas": ["price", "features"]
}
```

## Output
```json
{
  "change_detected": true,
  "change_score": 0.85,
  "summary": "Price increased by 20%.",
  "diff_snippet": "- Price: $10\n+ Price: $12"
}
```
