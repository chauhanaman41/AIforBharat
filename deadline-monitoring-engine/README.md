# Engine 16 — Deadline Monitoring Engine

> Tracks scheme deadlines and generates urgency-scored alerts.

| Property | Value |
|----------|-------|
| **Port** | 8016 |
| **Folder** | `deadline-monitoring-engine/` |
| **Database Tables** | `scheme_deadlines`, `user_deadline_alerts` |

## Run

```bash
uvicorn deadline-monitoring-engine.main:app --port 8016 --reload
```

Docs: http://localhost:8016/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/deadlines/check` | Check upcoming deadlines for user's eligible schemes |
| GET | `/deadlines/list` | List all tracked deadlines |
| POST | `/deadlines/add` | Add a new scheme deadline |
| GET | `/deadlines/user/{user_id}/history` | User's deadline alert history |

## Seed Deadlines

5 pre-loaded deadlines:

| Scheme | Deadline | Priority |
|--------|----------|----------|
| PM-KISAN | 2025-03-31 | important |
| PMAY | 2025-06-30 | urgent |
| Sukanya Samriddhi | 2025-12-31 | info |
| SC/ST Post-Matric Scholarship | 2025-01-31 | critical |
| PM MUDRA | 2025-09-30 | important |

## Urgency Scoring

Score range: **0.0 – 1.0**

| Formula Component | Weight |
|-------------------|--------|
| Days remaining (closer = higher) | Primary |
| Priority level multiplier | Secondary |

| Priority | Multiplier |
|----------|:----------:|
| info | 0.5 |
| important | 0.7 |
| urgent | 0.9 |
| critical | 1.0 |
| overdue | 1.0 (score = 1.0) |

## Request Models

- `CheckDeadlinesRequest` — `user_id`, `scheme_ids` (optional filter)
- `AddDeadlineRequest` — `scheme_id`, `scheme_name`, `deadline_date`, `priority`, `description`, `application_url`

## Events Published

- `DEADLINE_CREATED` — when new deadline added
- `DEADLINE_ESCALATED` — when deadline urgency reaches critical

## Gateway Route

`/api/v1/deadlines/*` → proxied from API Gateway (JWT auth required)

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **User Onboarding** | `POST /api/v1/onboard` | Check upcoming deadlines for new user (parallel with E15) | Step 6 of 8 |
| **Voice Query** | `POST /api/v1/voice-query` | Deadline check when intent is `deadline` | Conditional |

### Flow Detail: User Onboarding

```
E1 (Register) → E2 (Identity) → E4 (Metadata) → E5 (Processed Meta)
  → E15 (Eligibility) ∥ E16 (Deadlines) → E12 (Profile) → E3+E13 (Audit)
```

E16 runs in **parallel** with E15 during onboarding. It evaluates all active deadlines against the user's state/profile and returns urgency-scored alerts. Failure is **non-critical** — onboarding completes without deadline info.

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/deadlines/check` during onboarding and voice queries |
| **Called by** | API Gateway (Proxy) | All `/deadlines/*` routes for direct access |
| **Feeds** | JSON User Info Gen (E12) | `deadline_info` section in user profiles |
| **Feeds** | Dashboard (E14) | Upcoming deadlines widget |
| **Publishes to** | Event Bus → E3, E13 | `DEADLINE_CREATED`, `DEADLINE_ESCALATED` |

## Shared Module Dependencies

- `shared/config.py` — `settings` (port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`, `DeadlinePriority`
- `shared/event_bus.py` — `event_bus`
- `shared/utils.py` — `generate_id()`, `days_until()`
