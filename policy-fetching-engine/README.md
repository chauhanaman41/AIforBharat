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
