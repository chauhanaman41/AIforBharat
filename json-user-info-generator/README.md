# Engine 12 — JSON User Info Generator

> Assembles comprehensive user profiles from all platform data sources.

| Property | Value |
|----------|-------|
| **Port** | 8012 |
| **Folder** | `json-user-info-generator/` |
| **Database Tables** | `generated_profiles` |

## Run

```bash
uvicorn json-user-info-generator.main:app --port 8012 --reload
```

Docs: http://localhost:8012/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/profile/generate` | Assemble comprehensive user JSON profile |
| GET | `/profile/{user_id}` | Get latest generated profile |
| GET | `/profile/{user_id}/summary` | Compact summary for AI prompts |

## Profile Sections

The generated profile aggregates data from multiple engines:

| Section | Source Engine | Contents |
|---------|-------------|----------|
| `personal_info` | Engine 2 (Identity) | Name, phone, gender |
| `demographic_info` | Engine 5 (Metadata Store) | State, district, age |
| `economic_info` | Engine 5 | Income, occupation, land |
| `derived_attributes` | Engine 4 (Metadata) | Age group, income bracket, life stage, BPL |
| `eligibility_summary` | Engine 15 (Eligibility) | Per-scheme verdicts |
| `trust_info` | Engine 19 (Trust) | Trust score and level |
| `risk_info` | Engine 8 (Anomaly) | Risk score and anomalies |
| `deadline_info` | Engine 16 (Deadline) | Upcoming deadlines |
| `completeness` | Computed | Percentage of fields filled |

## Compact Summary

`GET /profile/{user_id}/summary` returns a minimal JSON blob optimized for AI system prompts — includes key demographics, top eligible schemes, and trust level without verbose details.

## Request Models

- `GenerateProfileRequest` — `user_id`, `include_sections` (optional list to limit output)

## Gateway Route

`/api/v1/profile/*` → proxied from API Gateway (JWT auth required)

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **User Onboarding** | `POST /api/v1/onboard` | Generate comprehensive user profile JSON | Step 7 of 8 |

### Flow Detail: User Onboarding

```
E1 (Register) → E2 (Identity) → E4 (Metadata) → E5 (Processed Meta)
  → E15 ∥ E16 (Eligibility + Deadlines) → E12 (Profile) → E3+E13 (Audit)
```

E12 is the **final assembly step** before audit. It aggregates data from E4 (metadata), E15 (eligibility results), and E16 (deadlines) into a comprehensive user profile JSON. The profile includes a `completeness` score returned to the client. Failure is **non-critical**.

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/profile/generate` during onboarding |
| **Called by** | API Gateway (Proxy) | All `/profile/*` routes for direct access |
| **Reads from** | Identity Engine (E2) | `personal_info` section |
| **Reads from** | Processed Metadata (E5) | `demographic_info`, `economic_info` sections |
| **Reads from** | Metadata Engine (E4) | `derived_attributes` section |
| **Reads from** | Eligibility Rules (E15) | `eligibility_summary` section |
| **Reads from** | Trust Scoring (E19) | `trust_info` section |
| **Reads from** | Anomaly Detection (E8) | `risk_info` section |
| **Reads from** | Deadline Monitoring (E16) | `deadline_info` section |
| **Publishes to** | Event Bus → E3, E13 | `PROFILE_GENERATED` |

## Shared Module Dependencies

- `shared/config.py` — `settings` (port, engine URLs)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`
- `shared/event_bus.py` — `event_bus`
- `shared/utils.py` — `generate_id()`
- `shared/cache.py` — `LocalCache`
