# Engine 9 — API Gateway

> Single entry point for the entire AIforBharat platform.

| Property | Value |
|----------|-------|
| **Port** | 8000 |
| **Folder** | `api-gateway/` |
| **Files** | `main.py`, `routes.py`, `middleware.py` |

## Run

```bash
uvicorn api-gateway.main:app --port 8000 --reload
```

Docs: http://localhost:8000/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/` | Service directory with all route prefixes |
| ALL | `/api/v1/auth/*` | Proxy → Engine 1 (Login/Register) |
| ALL | `/api/v1/identity/*` | Proxy → Engine 2 (Identity) — auth required |
| ALL | `/api/v1/metadata/*` | Proxy → Engine 4 (Metadata) — auth required |
| ALL | `/api/v1/eligibility/*` | Proxy → Engine 15 (Eligibility) — auth required |
| ALL | `/api/v1/schemes/*` | Proxy → Engine 11 (Policy Fetching) |
| ALL | `/api/v1/policies/*` | Proxy → Engine 11 (Policy Fetching) |
| ALL | `/api/v1/simulate/*` | Proxy → Engine 17 (Simulation) — auth required |
| ALL | `/api/v1/deadlines/*` | Proxy → Engine 16 (Deadline) — auth required |
| ALL | `/api/v1/ai/*` | Proxy → Engine 7 (Neural Network) — auth required |
| ALL | `/api/v1/dashboard/*` | Proxy → Engine 14 (Dashboard) — auth required |
| ALL | `/api/v1/documents/*` | Proxy → Engine 21 (Doc Understanding) — auth required |
| ALL | `/api/v1/voice/*` | Proxy → Engine 20 (Speech) — auth required |
| ALL | `/api/v1/analytics/*` | Proxy → Engine 13 (Analytics) — auth required |
| ALL | `/api/v1/trust/*` | Proxy → Engine 19 (Trust Scoring) — auth required |
| ALL | `/api/v1/profile/*` | Proxy → Engine 12 (JSON User Info) — auth required |
| GET | `/api/v1/debug/events` | Event bus history (dev only) — auth required |

## Middleware Stack

1. **CORS** — allows localhost origins (5173, 3000, 8000)
2. **TrustedHostMiddleware** — all hosts allowed in dev
3. **RateLimitMiddleware** — token bucket: 100 requests/minute per IP, returns 429 with `Retry-After`
4. **RequestLoggingMiddleware** — logs method, path, status, latency; adds `X-Response-Time` header
5. **Request ID Middleware** — attaches `X-Request-ID` to every request for tracing

## Authentication

Routes marked "auth required" validate the `Authorization: Bearer <token>` header via JWT decode. The `/api/v1/auth/*` routes are unauthenticated (registration and login).

## Files

- `main.py` — FastAPI app, middleware stack, health/root endpoints, exception handler
- `routes.py` — Router with proxy functions for all 16 route groups
- `middleware.py` — `RateLimitMiddleware`, `RequestLoggingMiddleware`
- `orchestrator.py` — Composite routes that chain multiple engines in sequence (the "conductor")

## Orchestrator Layer

The API Gateway hosts the **Orchestrator** — 6 composite routes that chain multiple engines into cohesive end-to-end pipelines. The orchestrator lives inside the gateway (no separate engine).

### Architecture Decisions

- **Hub-and-Spoke:** Only the API Gateway makes cross-engine HTTP calls via `httpx.AsyncClient`
- **Circuit Breaker:** Per-engine failure tracking (5 failures → OPEN → 30s recovery → HALF_OPEN probe)
- **Audit:** Every composite flow ends with a fire-and-forget POST to E3 (Raw Data Store) + E13 (Analytics)
- **Graceful Degradation:** Non-critical steps return `degraded: [...]` instead of failing the whole flow
- **Correlation IDs:** Every call carries `X-Request-ID` for end-to-end tracing

### 6 Composite Routes

| # | Route | Type | Pipeline | Auth |
|---|-------|------|----------|------|
| 1 | `POST /api/v1/query` | Agent Flow | E7(intent) → E6(search) → E7(RAG) → E8∥E19(anomaly+trust) → Audit | JWT |
| 2 | `POST /api/v1/onboard` | Controller Flow | E1 → E2 → E4 → E5 → E15∥E16 → E12 → Audit | None |
| 3 | `POST /api/v1/check-eligibility` | Controller Flow | E15 → E7(explain) → Audit | JWT |
| 4 | `POST /api/v1/ingest-policy` | Controller Flow | E11 → E21 → E10 → E7(embed) → E6(upsert) → E4 → Audit | JWT |
| 5 | `POST /api/v1/voice-query` | Agent Flow | E7(intent) → Route → E20(TTS) → Audit | None |
| 6 | `POST /api/v1/simulate` | Controller Flow | E17 → E7(explain) → Audit | JWT |

### Flow Types

- **Controller Flow:** Deterministic sequential steps — no LLM decision-making in routing. Every step is hardcoded.
- **Agent Flow:** Dynamic routing based on intent classification from Neural Network Engine (E7).

### Request Schemas

| Schema | Fields | Used By |
|--------|--------|---------|
| `QueryRequest` | `message`, `user_id`, `session_id?`, `top_k` | `/query` |
| `OnboardRequest` | `phone`, `password`, `name`, `state?`, `district?`, `language_preference`, ... (14 optional profile fields) | `/onboard` |
| `EligibilityRequest` | `user_id`, `profile`, `scheme_ids?`, `explain` | `/check-eligibility` |
| `IngestPolicyRequest` | `source_url`, `source_type`, `tags?` | `/ingest-policy` |
| `VoiceQueryRequest` | `text`, `language`, `user_id?` | `/voice-query` |
| `SimulateRequest` | `user_id`, `current_profile`, `changes`, `explain` | `/simulate` |

### Engine Participation Matrix

| Engine | Query | Onboard | Eligibility | Ingest | Voice | Simulate |
|--------|:-----:|:-------:|:-----------:|:------:|:-----:|:--------:|
| E1 Login/Register | | **Step 1** | | | | |
| E2 Identity | | Step 2 | | | | |
| E3 Raw Data Store | Audit | Audit | Audit | Audit | Audit | Audit |
| E4 Metadata | | Step 3 | | Step 6 | | |
| E5 Processed Meta | | Step 4 | | | | |
| E6 Vector DB | Step 2 | | | Step 5 | Cond. | |
| E7 Neural Network | Steps 1,3 | | Step 2 | Step 4 | Steps 1-3 | Step 2 |
| E8 Anomaly | Step 4∥ | | | | | |
| E10 Chunks | | | | Step 3 | | |
| E11 Policy Fetch | | | | **Step 1** | | |
| E12 JSON User Info | | Step 7 | | | | |
| E13 Analytics | Audit | Audit | Audit | Audit | Audit | Audit |
| E15 Eligibility | | Step 5∥ | **Step 1** | | Cond. | |
| E16 Deadline | | Step 6∥ | | | Cond. | |
| E17 Simulation | | | | | | **Step 1** |
| E19 Trust Scoring | Step 5∥ | | | | | |
| E20 Speech | | | | | Step 4 | |
| E21 Doc Understanding | | | | Step 2 | | |

> **Bold** = critical (failure aborts flow). ∥ = parallel. Cond. = conditional on intent.

### System Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/circuit-breaker/status` | View circuit breaker states for all engines |
| GET | `/api/v1/engines/health` | Probe health of all 21 engines concurrently |

## Shared Module Dependencies

- `shared/config.py` — `ENGINE_URLS` (all engine base URLs), `settings`
- `shared/models.py` — `ApiResponse` (response envelope for all routes)
