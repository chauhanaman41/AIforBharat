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

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **RAG Query** | `POST /api/v1/query` | Check AI response for anomalies (parallel with E19) | Step 4 of 6 |

### Flow Detail: RAG Query

```
E7 (Intent) → E6 (Vector Search) → E7 (RAG Generate)
  → E8 (Anomaly) ∥ E19 (Trust) → E3+E13 (Audit)
```

E8 runs in **parallel** with E19 (Trust Scoring). It analyzes the AI-generated response for inconsistencies. Failure is **non-critical** — the response is still returned but flagged as `degraded: ["anomaly_check"]`.

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/anomaly/check` during RAG queries (parallel) |
| **Called by** | Trust Scoring (E19) | Profile anomaly assessment as scoring component |
| **Called by** | JSON User Info Generator (E12) | Risk info for user profiles |
| **Publishes to** | Event Bus → E3, E13 | `ANOMALY_DETECTED`, `ANOMALY_RESOLVED` |

## Shared Module Dependencies

- `shared/config.py` — `settings` (port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`
- `shared/event_bus.py` — `event_bus`
- `shared/utils.py` — `generate_id()`
