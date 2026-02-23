# Contract: web_scraper_v1

## Objective
Extract main text content and metadata from a URL.

## Input
```json
{
  "url": "https://example.com/blog/post",
  "include_html": false
}
```

## Output
```json
{
  "title": "Blog Post Title",
  "text_content": "Full article text...",
  "status_code": 200
}
```
