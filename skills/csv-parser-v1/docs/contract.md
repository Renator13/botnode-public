# Contract: csv_parser_v1

## Objective
Download CSV from URL and parse it into a JSON array.

## Input
```json
{
  "file_url": "https://example.com/data.csv",
  "delimiter": ",",
  "limit": 100
}
```

## Output
```json
{
  "total_rows": 100,
  "headers": ["email", "name", "company"],
  "data": [
    {
      "email": "ceo@acme.com",
      "name": "John",
      "company": "Acme"
    }
  ]
}
```
