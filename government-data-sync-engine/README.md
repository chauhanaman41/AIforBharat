# Engine 18 — Government Data Sync Engine

> Synchronizes government datasets (Census, NFHS, SDG) from data.gov.in and other open data portals.

| Property | Value |
|----------|-------|
| **Port** | 8018 |
| **Folder** | `government-data-sync-engine/` |
| **Database Tables** | `synced_datasets`, `gov_data_records` |

## Run

```bash
uvicorn government-data-sync-engine.main:app --port 8018 --reload
```

Docs: http://localhost:8018/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/gov-data/sync` | Sync a dataset (local-first: checks cache first) |
| POST | `/gov-data/query` | Query data with state/district/year filters |
| GET | `/gov-data/datasets` | List all synced datasets (filterable by category) |
| GET | `/gov-data/dataset/{dataset_id}` | Get dataset details + sample records |
| POST | `/gov-data/datasets/add` | Add custom dataset with records |

## Seed Datasets

| Dataset ID | Name | Category | Records |
|-----------|------|----------|:-------:|
| `nfhs5_district` | NFHS-5 District Factsheet Data | nfhs | 5 |
| `census_2011_population` | Census 2011 Population Data | census | — |
| `sdg_india_index` | SDG India Index | sdg | — |
| `poverty_headcount` | Poverty Headcount Ratio | economic | 6 |
| `scheme_beneficiaries` | Scheme Beneficiary Statistics | schemes | 5 |

## Local-First Data Caching

1. On sync request, **checks if dataset is already cached locally**
2. If cached and `force_refresh=false`, returns cached data immediately
3. If `force_refresh=true`, re-syncs from source
4. All data stored as JSON files in `data/gov-data/` directory
5. Content hash tracked for change detection

## Query Filters

```bash
POST /gov-data/query
{
  "dataset_id": "poverty_headcount",
  "state": "Bihar",
  "year": "2011-12",
  "limit": 50
}
```

Supports case-insensitive partial matching on `state` and `district`.

## Request Models

- `SyncDatasetRequest` — `dataset_id`, `force_refresh`
- `QueryDataRequest` — `dataset_id`, `state`, `district`, `year`, `limit`
- `AddDatasetRequest` — `dataset_id`, `name`, `source`, `category`, `description`, `records` (list of dicts)

## Gateway Route

Not directly exposed via gateway. Used internally by Dashboard and Analytics engines.
