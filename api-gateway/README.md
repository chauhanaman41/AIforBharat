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
