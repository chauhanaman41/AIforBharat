# Engine 5 — Processed User Metadata Store

> Persistent encrypted storage for processed user profiles, eligibility cache, and risk scores.

| Property | Value |
|----------|-------|
| **Port** | 8005 |
| **Folder** | `processed-user-metadata-store/` |
| **Database Tables** | `user_metadata`, `user_derived_attributes`, `user_eligibility_cache`, `user_risk_scores` |

## Run

```bash
uvicorn processed-user-metadata-store.main:app --port 8005 --reload
```

Docs: http://localhost:8005/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/processed-metadata/store` | Store processed user metadata |
| GET | `/processed-metadata/user/{user_id}` | Get full user metadata + derived attributes |
| PUT | `/processed-metadata/user/{user_id}` | Update specific metadata fields |
| DELETE | `/processed-metadata/user/{user_id}` | Delete all user data (DPDP right-to-erasure) |
| POST | `/processed-metadata/eligibility/cache` | Cache eligibility verdict |
| GET | `/processed-metadata/eligibility/{user_id}` | Get cached eligibility results |
| POST | `/processed-metadata/risk` | Store risk score |
| GET | `/processed-metadata/risk/{user_id}` | Get user risk scores |

## Data Model

### UserMetadata
Core profile: `user_id`, `full_name`, `phone`, `age`, `gender`, `state`, `district`, `annual_income`, `occupation`, `caste_category`, `education`, `marital_status`

### UserDerivedAttributes
Computed: `age_group`, `income_bracket`, `life_stage`, `tax_bracket`, `employment_category`, `farmer_category`, `bpl_status`, `is_sc_st`, `is_obc`, `is_ews`

### UserEligibilityCache
Cached verdicts: `scheme_id`, `verdict`, `confidence`, `matched_criteria`, `expires_at`

### UserRiskScore
Risk assessments: `risk_type`, `score`, `details`

## DPDP Compliance

`DELETE /processed-metadata/user/{user_id}` performs complete erasure: deletes metadata, derived attributes, eligibility cache, and risk scores for the user.

## Gateway Route

Not directly exposed via gateway. Used internally by Metadata Engine (4), Eligibility Rules (15), and JSON User Info Generator (12).

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **User Onboarding** | `POST /api/v1/onboard` | Persist processed user metadata | Step 4 of 8 |

### Flow Detail: User Onboarding

```
E1 (Register) → E2 (Identity) → E4 (Metadata) → E5 (Processed Meta)
  → E15 ∥ E16 (Eligibility + Deadlines) → E12 (Profile) → E3+E13 (Audit)
```

E5 receives normalized metadata from E4 and persists it for rapid retrieval by eligibility checks (E15) and profile generation (E12). Failure is **non-critical** — downstream engines will use in-memory data from E4.

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/processed-metadata/store` during onboarding |
| **Fed by** | Metadata Engine (E4) | Receives normalized + derived attributes |
| **Read by** | Eligibility Rules (E15) | Retrieved during eligibility checks |
| **Read by** | JSON User Info Generator (E12) | Profile assembly reads stored metadata |
| **Read by** | Trust Scoring (E19) | Data completeness assessment |

## Shared Module Dependencies

- `shared/config.py` — `settings` (AES encryption key, port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`
- `shared/event_bus.py` — `event_bus`
- `shared/utils.py` — `generate_id()`
