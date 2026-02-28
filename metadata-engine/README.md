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
