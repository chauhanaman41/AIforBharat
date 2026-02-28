# Engine 17 — Simulation Engine

> What-if analysis and life event impact simulation.

| Property | Value |
|----------|-------|
| **Port** | 8017 |
| **Folder** | `simulation-engine/` |
| **Database Tables** | `simulation_records` |

## Run

```bash
uvicorn simulation-engine.main:app --port 8017 --reload
```

Docs: http://localhost:8017/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/simulate/what-if` | Compare eligibility between base and modified profiles |
| POST | `/simulate/life-event` | Simulate life event impact on eligibility |
| POST | `/simulate/compare` | Side-by-side comparison of two profiles |
| GET | `/simulate/history/{user_id}` | User's simulation history |

## What-If Analysis

Compare a base profile against a modified profile to see:
- **Schemes gained** — newly eligible after changes
- **Schemes lost** — no longer eligible after changes
- **Benefit change** — total annual benefit difference (₹)

## Life Events

| Event | Profile Changes |
|-------|----------------|
| `marriage` | marital_status → married, +1 dependent |
| `child_born` | +1 dependent, has_daughter flag |
| `job_loss` | occupation → unemployed, income → 0 |
| `retirement` | occupation → retired, income × 0.4 |
| `relocation` | state change |
| `promotion` | income × 1.5 |

## Scheme Rules (Self-Contained)

8 schemes with built-in benefit values:

| Scheme | Annual Benefit |
|--------|:-------------:|
| PM-KISAN | ₹6,000 |
| PMAY | ₹2,67,000 |
| PMJAY | ₹5,00,000 |
| PM Ujjwala | ₹1,600 |
| PM MUDRA | ₹50,000 |
| PMSBY | ₹2,00,000 |
| PMJJBY | ₹2,00,000 |
| SC/ST Scholarship | ₹36,000 |

## Request Models

- `SimulateRequest` — `user_id` (str, required), `current_profile` (dict, required), `changes` (dict, required), `scenario_type` (str, default `"custom"`)
- `LifeEventRequest` — `user_id` (str, required), `current_profile` (dict, required), `life_event` (str, required), `event_params` (dict, default `{}`)
- `CompareRequest` — `profile_a`, `profile_b`

## Gateway Route

`/api/v1/simulate/*` → proxied from API Gateway (JWT auth required)
