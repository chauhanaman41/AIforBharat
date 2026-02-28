# Engine 14 — Dashboard Interface

> Backend-for-Frontend (BFF) layer aggregating data for the dashboard UI.

| Property | Value |
|----------|-------|
| **Port** | 8014 |
| **Folder** | `dashboard-interface/` |
| **Database Tables** | `dashboard_preferences` |

## Run

```bash
uvicorn dashboard-interface.main:app --port 8014 --reload
```

Docs: http://localhost:8014/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/dashboard/home/{user_id}` | Main dashboard (widgets, navigation, quick actions) |
| GET | `/dashboard/schemes` | Schemes listing page data (10 major schemes) |
| GET | `/dashboard/engines/status` | Health status of all 21 engines with ports |
| GET | `/dashboard/preferences/{user_id}` | Get user dashboard preferences |
| PUT | `/dashboard/preferences/{user_id}` | Update preferences (theme, language, widgets) |
| GET | `/dashboard/search?q=...` | Global search across schemes and features |

## Widgets

The dashboard home endpoint returns 8 configurable widgets:

| Widget | Description | Icon |
|--------|-------------|------|
| `eligibility_summary` | Your eligible schemes | shield-check |
| `popular_schemes` | Trending schemes | trending-up |
| `upcoming_deadlines` | Deadline alerts | clock |
| `trust_score` | Your trust score | award |
| `profile_completeness` | Profile fill percentage | user-check |
| `what_if` | What-If Simulator | sliders |
| `ai_assistant` | AI Chat | message-circle |
| `voice_assistant` | Voice Assistant (multilingual) | mic |

## User Preferences

| Setting | Options | Default |
|---------|---------|---------|
| `theme` | light, dark | light |
| `language` | english, hindi, tamil, etc. | english |
| `widget_order` | Reorderable widget list | All 8 in default order |
| `notifications_enabled` | true / false | true |

## Global Search

`GET /dashboard/search?q=kisan` searches across:
- **Schemes** — keyword matching against known scheme aliases
- **Features** — matches eligibility, simulate, chat, voice, document, deadline

## Gateway Route

`/api/v1/dashboard/*` → proxied from API Gateway (JWT auth required)

## Orchestrator Integration

This engine does **not participate** in any of the 6 composite orchestrator flows. It is a standalone **Backend-for-Frontend (BFF)** layer that aggregates data from other engines for the dashboard UI.

### Standalone Role

The Dashboard BFF reads from multiple engines on demand when rendering dashboard views:

| Data Source | Engine | Purpose |
|-------------|--------|--------|
| Eligibility summary | E15 | Widget: eligible scheme count |
| Upcoming deadlines | E16 | Widget: deadline alerts |
| Trust score | E19 | Widget: user trust level |
| Profile completeness | E12 | Widget: profile completion % |
| Scheme popularity | E13 | Widget: trending schemes |
| Engine health | All engines | Operations: system status page |

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Proxy) | All `/dashboard/*` routes |
| **Reads from** | Eligibility Rules (E15) | Eligibility summary for homepage widget |
| **Reads from** | Deadline Monitoring (E16) | Upcoming deadlines for alerts widget |
| **Reads from** | Trust Scoring (E19) | Trust score for profile widget |
| **Reads from** | JSON User Info Gen (E12) | Profile completeness metric |
| **Reads from** | Analytics Warehouse (E13) | Scheme popularity, funnel data |
| **Probes** | All engines | `/health` endpoint for system status |

## Shared Module Dependencies

- `shared/config.py` — `settings` (port, engine URLs)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`
- `shared/cache.py` — `LocalCache`
- `shared/utils.py` — `generate_id()`
