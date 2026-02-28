# Engine 4 — Metadata Engine

> Normalizes and enriches raw user data into structured profiles.

| Property | Value |
|----------|-------|
| **Port** | 8004 |
| **Folder** | `metadata-engine/` |
| **Storage** | In-memory cache (L1 + L2 file) |

## Run

```bash
uvicorn metadata-engine.main:app --port 8004 --reload
```

Docs: http://localhost:8004/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/metadata/process` | Normalize & enrich raw user metadata |
| GET | `/metadata/user/{user_id}` | Get processed metadata from cache |
| POST | `/metadata/validate` | Validate individual fields |

## Derived Fields

From raw user input, computes:

| Field | Logic |
|-------|-------|
| `age_group` | minor / youth / young_adult / middle_aged / senior_citizen |
| `income_bracket` | below_2.5L / 2.5L-5L / 5L-10L / 10L-20L / above_20L |
| `life_stage` | student / early_career / family_building / established / pre_retirement / retired |
| `tax_bracket` | FY 2024-25 New Regime slabs (0% / 5% / 10% / 15% / 20% / 30%) |
| `employment_category` | unemployed / self_employed / salaried / business / government / retired |
| `farmer_category` | marginal / small / semi_medium / medium / large (by land holding) |
| `bpl_status` | Below Poverty Line (income < ₹1,20,000) |
| `is_sc_st` | SC/ST flag |
| `is_obc` | OBC flag |
| `is_ews` | EWS flag (General + income < ₹8,00,000) |

## Request Models

- `MetadataProcessRequest` — `user_id`, `age`, `date_of_birth`, `gender`, `state`, `district`, `annual_income`, `occupation`, `caste_category`, `land_holding_acres`, `education`, `marital_status`, `dependents`
- `MetadataValidateRequest` — `field_name`, `field_value`

## Gateway Route

`/api/v1/metadata/*` → proxied from API Gateway (JWT auth required)

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **User Onboarding** | `POST /api/v1/onboard` | Normalize raw user profile into structured metadata | Step 3 of 8 |
| **Policy Ingestion** | `POST /api/v1/ingest-policy` | Tag ingested policy with metadata | Step 6 of 7 |

### Flow Detail: User Onboarding

```
E1 (Register) → E2 (Identity) → E4 (Metadata) → E5 (Processed Meta)
  → E15 ∥ E16 (Eligibility + Deadlines) → E12 (Profile) → E3+E13 (Audit)
```

E4 normalizes raw inputs (state names, income, DOB) into clean structured fields with derived attributes (age_group, income_bracket, life_stage, etc.). Failure is **non-critical** — eligibility checks will use raw profile data.

### Flow Detail: Policy Ingestion

```
E11 (Fetch) → E21 (Parse) → E10 (Chunk) → E7 (Embed) → E6 (Vector Upsert)
  → E4 (Tag Metadata) → E3+E13 (Audit)
```

E4 tags the ingested policy document with structured metadata (scheme_type, state, ministry). This step is **fire-and-forget** — failure doesn't block ingestion.

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/metadata/process` during onboarding and policy ingestion |
| **Called by** | API Gateway (Proxy) | All `/metadata/*` routes for direct access |
| **Feeds into** | Processed Metadata (E5) | Normalized profiles stored for later retrieval |
| **Feeds into** | Eligibility Rules (E15) | Clean profiles enable accurate rule matching |
| **Publishes to** | Event Bus → E3, E13 | `METADATA_PROCESSED`, `METADATA_VALIDATED` |

## Shared Module Dependencies

- `shared/config.py` — `settings` (port)
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`
- `shared/event_bus.py` — `event_bus`
- `shared/utils.py` — `generate_id()`, `INDIAN_STATES`
- `shared/cache.py` — `LocalCache`
