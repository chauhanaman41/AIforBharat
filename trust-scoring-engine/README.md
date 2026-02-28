# Engine 19 — Trust Scoring Engine

> Composite trust scoring system with weighted components.

| Property | Value |
|----------|-------|
| **Port** | 8019 |
| **Folder** | `trust-scoring-engine/` |
| **Database Tables** | `trust_score_records` |

## Run

```bash
uvicorn trust-scoring-engine.main:app --port 8019 --reload
```

Docs: http://localhost:8019/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/trust/compute` | Compute composite trust score (0-100) |
| GET | `/trust/user/{user_id}` | Get latest trust score |
| GET | `/trust/user/{user_id}/history` | Trust score history |

## Scoring Components

| Component | Weight | Description |
|-----------|:------:|-------------|
| `data_completeness` | 30% | Percentage of profile fields filled |
| `anomaly_check` | 25% | Inverse of anomaly risk score |
| `consistency` | 20% | Cross-field data consistency |
| `behavior` | 15% | Platform usage patterns |
| `verification` | 10% | **Stubbed at 0%** (DigiLocker not integrated) |

## Trust Levels

| Score | Level |
|:-----:|-------|
| 0 – 20 | UNVERIFIED |
| 21 – 40 | LOW |
| 41 – 60 | MEDIUM |
| 61 – 80 | HIGH |
| 81 – 100 | VERIFIED |

> **Note**: Maximum achievable trust level is ~90 without DigiLocker verification. The verification component (10%) is permanently 0% per design constraints.

## Request Models

- `ComputeTrustRequest` — `user_id`, `profile` (dict with name, phone, age, income, etc.)

## Events Published

- `TRUST_SCORE_COMPUTED` — on every trust score computation

## Dependencies

Internally checks data from:
- Anomaly Detection Engine (8) — for anomaly risk score
- Metadata Engine (4) — for field completeness

## Gateway Route

`/api/v1/trust/*` → proxied from API Gateway (JWT auth required)
