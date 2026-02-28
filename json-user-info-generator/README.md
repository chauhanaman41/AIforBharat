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
