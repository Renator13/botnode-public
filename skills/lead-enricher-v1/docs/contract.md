# Contract: lead_enricher_v1

## Objective
Enrich a domain or email with company information.

## Input
```json
{
  "domain": "stripe.com",
  "email": "patrick@stripe.com"
}
```

## Output
```json
{
  "company_name": "Stripe",
  "industry": "Fintech",
  "employees": 5000,
  "linkedin_url": "https://linkedin.com/company/stripe",
  "source": "mock_db"
}
```
