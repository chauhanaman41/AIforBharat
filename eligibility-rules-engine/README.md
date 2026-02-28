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

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **User Onboarding** | `POST /api/v1/onboard` | Batch eligibility check for new user (parallel with E16) | Step 5 of 8 |
| **Eligibility Check** | `POST /api/v1/check-eligibility` | Deterministic eligibility evaluation (critical first step) | Step 1 of 3 |
| **Voice Query** | `POST /api/v1/voice-query` | Eligibility check when intent is `eligibility_check` | Conditional |

### Flow Detail: User Onboarding

```
E1 (Register) → E2 (Identity) → E4 (Metadata) → E5 (Processed Meta)
  → E15 (Eligibility) ∥ E16 (Deadlines) → E12 (Profile) → E3+E13 (Audit)
```

E15 runs in **parallel** with E16 during onboarding. It evaluates the new user against all 10 built-in scheme rules and returns eligible/partial/not-eligible counts.

### Flow Detail: Eligibility Check with Explanation

```
→ E15 (Eligibility Check) → E7 (AI Explanation) → E3+E13 (Audit)
```

E15 is the **critical entry point** — if it fails, the entire flow aborts. The eligibility verdict is 100% deterministic (boolean logic, no LLM). E7 provides an optional human-readable explanation.

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/eligibility/check` during onboarding, check-eligibility, voice query |
| **Called by** | API Gateway (Proxy) | All `/eligibility/*` routes for direct access |
| **Fed by** | Metadata Engine (E4) | Normalized user profiles for accurate matching |
| **Fed by** | Processed Metadata (E5) | Stored profiles for historical checks |
| **Feeds** | Neural Network (E7) | Results text for AI explanation generation |
| **Feeds** | JSON User Info Gen (E12) | `eligibility_summary` section in user profiles |
| **Feeds** | Dashboard (E14) | Eligibility widget data |
| **Publishes to** | Event Bus → E3, E13 | `ELIGIBILITY_CHECKED` |

## Shared Module Dependencies

- `shared/config.py` — `settings` (port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`, `EligibilityVerdict`
- `shared/event_bus.py` — `event_bus`
- `shared/utils.py` — `generate_id()`
- `shared/cache.py` — `LocalCache`
