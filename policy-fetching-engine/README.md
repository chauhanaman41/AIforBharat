# Engine 11 — Policy Fetching Engine

> Data acquisition layer for government scheme documents.

| Property | Value |
|----------|-------|
| **Port** | 8011 |
| **Folder** | `policy-fetching-engine/` |
| **Database Tables** | `fetched_documents`, `source_configs` |

## Run

```bash
uvicorn policy-fetching-engine.main:app --port 8011 --reload
```

Docs: http://localhost:8011/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/policies/fetch` | Fetch & store a policy document (with change detection) |
| GET | `/policies/list` | List policies (filter by ministry, category, status) |
| GET | `/policies/{policy_id}` | Get policy with full content |
| GET | `/policies/{policy_id}/versions` | Version history of a policy |
| POST | `/policies/search` | Search policies by keyword or ministry |
| GET | `/policies/sources/list` | List configured data sources |
| POST | `/policies/sources/add` | Add a new crawl source |

## Seed Data

### 10 Pre-loaded Schemes

| Scheme | Category | Ministry |
|--------|----------|----------|
| PM-KISAN | Agriculture | Agriculture & Farmers Welfare |
| PMAY | Housing | Housing & Urban Affairs |
| Ayushman Bharat (PMJAY) | Health | Health & Family Welfare |
| PM Ujjwala Yojana | Energy | Petroleum & Natural Gas |
| PM MUDRA Yojana | Finance | Finance |
| PMSBY | Insurance | Finance |
| PMJJBY | Insurance | Finance |
| Sukanya Samriddhi | Savings | Finance |
| NPS | Pension | Finance |
| SC/ST Post-Matric Scholarship | Education | Social Justice |

### 5 Default Data Sources

- data.gov.in (API key configured)
- Gazette of India
- PM-KISAN Portal
- MyScheme Portal
- RBI Notifications

## Change Detection

On re-fetch, computes SHA-256 hash of content. If hash differs from stored version, creates a new version and publishes `POLICY_UPDATED` event.

## Gateway Route

`/api/v1/schemes/*` and `/api/v1/policies/*` → proxied from API Gateway (no auth required)

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **Policy Ingestion** | `POST /api/v1/ingest-policy` | Fetch and store policy document (critical first step) | Step 1 of 7 |

### Flow Detail: Policy Ingestion

```
→ E11 (Fetch) → E21 (Parse) → E10 (Chunk) → E7 (Embed) → E6 (Vector Upsert)
  → E4 (Tag Metadata) → E3+E13 (Audit)
```

E11 is the **critical entry point** for the ingestion pipeline. The orchestrator calls `POST /policies/fetch` with the policy content. E11 performs SHA-256 change detection — if the document is unchanged, it short-circuits with `change_type: "unchanged"`. If it fails, the entire pipeline aborts.

### Important: Orchestrator Endpoint Mapping

The orchestrator calls `POST /policies/fetch` (not `/schemes/fetch`). The request payload must match the `FetchRequest` schema:

```json
{
  "source_id": "string (required)",
  "url": "string (optional)",
  "document_type": "scheme",
  "content": "string (optional — the document text)",
  "metadata": { "title": "...", "policy_id": "..." }
}
```

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/policies/fetch` during policy ingestion |
| **Called by** | API Gateway (Proxy) | All `/policies/*` and `/schemes/*` routes for direct access |
| **Feeds** | Doc Understanding (E21) | Raw document text for structured parsing |
| **Feeds** | Chunks Engine (E10) | Raw text for chunking |
| **Publishes to** | Event Bus → E3, E13 | `DOCUMENT_FETCHED`, `DOCUMENT_UPDATED` |

## Shared Module Dependencies

- `shared/config.py` — `settings` (data directory, crawl settings, port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`
- `shared/event_bus.py` — `event_bus`
- `shared/utils.py` — `generate_id()`, `sha256_hash()`
- `shared/cache.py` — `LocalCache`
