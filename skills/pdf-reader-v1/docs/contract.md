# Contract: pdf_reader_v1

## Objective
Extract clean text and metadata from a PDF URL.

## Input
```json
{
  "file_url": "https://example.com/paper.pdf",
  "pages": "1-5",
  "extract_tables": false
}
```

## Output
```json
{
  "page_count": 5,
  "metadata": {
    "title": "Whitepaper v1",
    "author": "Satoshi"
  },
  "full_text": "Abstract...\n\nIntroduction..."
}
```
