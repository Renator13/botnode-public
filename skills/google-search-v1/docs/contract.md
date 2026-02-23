# Contract: google_search_v1

## Objective
Perform a search and return structured SERP-like results.

## Input
```json
{
  "query": "BotNode competitors",
  "num_results": 5
}
```

## Output
```json
{
  "results": [
    {
      "title": "Competitor A",
      "link": "https://comp-a.com",
      "snippet": "Leading AI agent platform..."
    }
  ]
}
```
