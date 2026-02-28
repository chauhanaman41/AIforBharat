# Engine 15 — Eligibility Rules Engine

> Deterministic rule-based scheme matching with human-readable explanations.

| Property | Value |
|----------|-------|
| **Port** | 8015 |
| **Folder** | `eligibility-rules-engine/` |
| **Database Tables** | `eligibility_rules`, `eligibility_results` |

## Run

```bash
uvicorn eligibility-rules-engine.main:app --port 8015 --reload
```

Docs: http://localhost:8015/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/eligibility/check` | Check eligibility across all/specified schemes |
| GET | `/eligibility/history/{user_id}` | Previous eligibility results |
| GET | `/eligibility/rules` | List all rules (filterable by scheme) |
| POST | `/eligibility/rules/add` | Add a custom eligibility rule |
| GET | `/eligibility/schemes` | List all schemes with rule counts |

## Built-in Rules

10 schemes with pre-loaded rules:

| Scheme | Key Criteria |
|--------|-------------|
| PM-KISAN | occupation=farmer, land ≤ 5 acres, income < ₹6L |
| PMAY | income < ₹18L, no existing house |
| Ayushman Bharat | income < ₹5L |
| PM Ujjwala | BPL household, gender=female |
| PM MUDRA | occupation in [self_employed, business], age 18-65 |
| PMSBY | age 18-70, income < ₹10L |
| PMJJBY | age 18-50, income < ₹10L |
| Sukanya Samriddhi | has_daughter=true, daughter_age < 10 |
| NPS | age 18-65 |
| SC/ST Scholarship | caste in [SC, ST], income < ₹2.5L, education ≥ post_matric |

## Rule Operators

`eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `in`, `not_in`, `contains`, `exists`

## Verdicts

| Verdict | Meaning |
|---------|---------|
| `ELIGIBLE` | All criteria matched |
| `PARTIAL_MATCH` | ≥ 50% criteria matched |
| `NOT_ELIGIBLE` | < 50% criteria matched |
| `NEEDS_VERIFICATION` | Missing required data |

## Example Response

```json
{
  "scheme": "PM-KISAN",
  "verdict": "ELIGIBLE",
  "confidence": 1.0,
  "matched": ["occupation is farmer", "land_holding ≤ 5 acres"],
  "unmatched": [],
  "explanation": "You are eligible for PM-KISAN. All 2 criteria matched."
}
```

## Gateway Route

`/api/v1/eligibility/*` → proxied from API Gateway (JWT auth required)
