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

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **Simulation** | `POST /api/v1/simulate` | Run what-if simulation (critical first step) | Step 1 of 3 |

### Flow Detail: Simulation with Explanation

```
→ E17 (What-If Simulation) → E7 (AI Explanation) → E3+E13 (Audit)
```

E17 is the **critical entry point** — if it fails, the entire flow aborts. The simulation is 100% deterministic (inline rules, no LLM). It compares `before` and `after` eligibility based on profile changes. E7 provides an optional human-readable explanation of the delta.

### Supported Changes

The orchestrator sends `current_profile` + `changes` dict. E17 applies changes and re-evaluates eligibility across 8 schemes with predefined benefit values.

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/simulate/what-if` during simulation flow |
| **Called by** | API Gateway (Proxy) | All `/simulate/*` routes for direct access |
| **Feeds** | Neural Network (E7) | Simulation results text for AI explanation generation |
| **Publishes to** | Event Bus → E3, E13 | `SIMULATION_RUN` |

## Shared Module Dependencies

- `shared/config.py` — `settings` (port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`
- `shared/event_bus.py` — `event_bus`
- `shared/utils.py` — `generate_id()`
- `shared/cache.py` — `LocalCache`
