# Engine 13 — Analytics Warehouse

> Platform-wide analytics, event tracking, metric snapshots, and funnel analysis.

| Property | Value |
|----------|-------|
| **Port** | 8013 |
| **Folder** | `analytics-warehouse/` |
| **Database Tables** | `analytics_events`, `metric_snapshots`, `funnel_steps` |

## Run

```bash
uvicorn analytics-warehouse.main:app --port 8013 --reload
```

Docs: http://localhost:8013/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/analytics/events` | Record an analytics event |
| POST | `/analytics/metrics` | Record a metric snapshot |
| POST | `/analytics/funnel` | Record a funnel step |
| GET | `/analytics/dashboard` | Platform-wide dashboard summary |
| GET | `/analytics/events/query` | Query events (filter by type, user, engine) |
| GET | `/analytics/metrics/query` | Query metric snapshots |
| GET | `/analytics/funnel/{funnel_name}` | Funnel drop-off analysis |
| GET | `/analytics/scheme-popularity` | Scheme popularity rankings |

## Event Bus Integration

Subscribes to **all events** (`*` wildcard) via the in-memory event bus. Automatically increments:

- **Event counters** — tracks frequency of each event type
- **Scheme popularity** — counts interactions per scheme
- **Engine call counts** — tracks which engines are most active
- **User action counts** — tracks per-user activity

## Funnel Analysis

Track user progression through multi-step flows:

```
Step 1: Registration       → 1000 users
Step 2: Profile Completion → 750 users  (25% drop-off)
Step 3: Eligibility Check  → 500 users  (33% drop-off)
Step 4: Scheme Application → 200 users  (60% drop-off)
```

## Dashboard Summary

`GET /analytics/dashboard` returns:
- Total events, unique users
- Top 10 event types, schemes, engines by activity
- Platform uptime

## Request Models

- `RecordEventRequest` — `event_type`, `user_id`, `engine`, `payload`
- `RecordMetricRequest` — `metric_name`, `metric_value`, `dimension`, `dimension_value`
- `FunnelStepRequest` — `funnel_name`, `step_name`, `step_order`, `user_id`

## Gateway Route

`/api/v1/analytics/*` → proxied from API Gateway (JWT auth required)
