# Engine 8 — Anomaly Detection Engine

> Rule-based anomaly detection for user profile data.

| Property | Value |
|----------|-------|
| **Port** | 8008 |
| **Folder** | `anomaly-detection-engine/` |
| **Database Tables** | `anomaly_records` |

## Run

```bash
uvicorn anomaly-detection-engine.main:app --port 8008 --reload
```

Docs: http://localhost:8008/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/anomaly/check` | Run anomaly detection on a user profile |
| GET | `/anomaly/user/{user_id}` | Get anomaly records for a user |
| PUT | `/anomaly/{anomaly_id}/resolve` | Mark anomaly as resolved / false positive |
| GET | `/anomaly/stats` | Global anomaly statistics |

## Detection Rules

| Check | What It Detects |
|-------|----------------|
| `check_income_anomalies` | Income < 0, senior citizen with high income, farmer income vs land mismatch |
| `check_age_anomalies` | Age < 0 or > 120, retired person under 40 |
| `check_data_quality` | Missing required fields (name, phone, state, income, age) |
| `check_duplicate_patterns` | Repeated identical values in names/phones |

## Risk Scoring

Aggregate risk score: `0.6 × max_severity + 0.4 × avg_severity`

| Score Range | Level |
|------------|-------|
| 0.0 – 0.3 | Low |
| 0.3 – 0.6 | Medium |
| 0.6 – 0.8 | High |
| 0.8 – 1.0 | Critical |

## Request Models

- `AnomalyCheckRequest` — `user_id`, `profile` (dict with age, income, occupation, etc.)
- `ResolveAnomalyRequest` — `resolution` (string), `is_false_positive` (bool)

## Events Published

- `ANOMALY_DETECTED` — when anomaly score > 0

## Gateway Route

Not directly exposed via gateway. Called by Trust Scoring Engine (19) and JSON User Info Generator (12).
