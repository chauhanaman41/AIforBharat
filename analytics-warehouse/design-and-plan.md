# Analytics Warehouse Engine — Design & Plan

## 1. Purpose

The Analytics Warehouse is the **OLAP (Online Analytical Processing) engine** for the AIforBharat platform, providing columnar, time-series, and aggregated analytics across all citizen profiles, scheme adoption rates, regional impact metrics, and platform health. It enables data-driven governance insights — from state-level scheme penetration heatmaps to individual impact predictions — while maintaining strict anonymization and privacy boundaries.

This engine does NOT serve real-time user requests. Instead, it processes batch/streaming data from upstream engines and serves pre-computed analytics to the Dashboard Interface, admin consoles, and research APIs.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Scheme Adoption Analytics** | Track enrollment rates, completion rates, and benefit disbursement by region/demographic |
| **Regional Heatmaps** | State → district → block level penetration metrics for every active scheme |
| **Impact Modeling** | Correlate scheme participation with economic outcomes using RAPIDS XGBoost on GPU |
| **Budget Effect Analysis** | Model fiscal impact of scheme modifications (e.g., "What if eligibility cap increases by 20%?") |
| **Cohort Analysis** | Segment users by demographics, behavior, and scheme participation patterns |
| **Time-Series Analytics** | Track metric evolution over time (enrollment trends, deadline compliance rates) |
| **Anomaly Alerting** | Detect unusual patterns in scheme adoption or platform usage |
| **Data Cube Generation** | Pre-compute multi-dimensional aggregates for sub-second dashboard queries |
| **Anonymized Research Export** | k-anonymity compliant data exports for academic/policy research |

---

## 3. Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                     Analytics Warehouse                        │
│                                                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │  Ingestion Layer  │  │  Compute Layer   │  │  Serving    │ │
│  │                   │  │                  │  │  Layer      │ │
│  │ Kafka Consumer   │  │ RAPIDS cuDF/cuML │  │             │ │
│  │ CDC Connector    │  │ dbt transforms   │  │ Pre-computed│ │
│  │ Batch Loader     │  │ Spark (optional) │  │ Data Cubes  │ │
│  └────────┬──────────┘  └────────┬─────────┘  └──────┬──────┘ │
│           │                      │                    │        │
│  ┌────────▼──────────────────────▼────────────────────▼──────┐ │
│  │                  Storage Layer                             │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌─────────────┐  ┌──────────────────┐   │ │
│  │  │ ClickHouse │  │ Apache      │  │ TimescaleDB      │   │ │
│  │  │ (OLAP)     │  │ Iceberg     │  │ (Time-Series)    │   │ │
│  │  │            │  │ (Data Lake) │  │                   │   │ │
│  │  │ Real-time  │  │ Historical  │  │ Metrics &        │   │ │
│  │  │ aggregates │  │ archive     │  │ KPIs over time   │   │ │
│  │  └────────────┘  └─────────────┘  └──────────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │  Query Engine    │  │  Export Engine    │                   │
│  │                  │  │                  │                   │
│  │ SQL interface   │  │ k-anonymity      │                   │
│  │ GraphQL API     │  │ Parquet export   │                   │
│  │ Data cube query │  │ Research APIs    │                   │
│  └──────────────────┘  └──────────────────┘                   │
└───────────────────────────────────────────────────────────────┘

Data Flow:
  Profile Snapshots ──┐
  Eligibility Events ──┤
  Scheme Adoptions ────┤──▶ Kafka ──▶ Ingestion Layer ──▶ ClickHouse
  Deadline Outcomes ───┤                                  Iceberg
  Platform Metrics ────┘                                  TimescaleDB
```

---

## 4. Data Models

### 4.1 ClickHouse — Scheme Adoption Fact Table

```sql
CREATE TABLE scheme_adoption_facts (
    event_date        Date,
    event_timestamp   DateTime64(3),
    user_id_hash      String,          -- Anonymized hash
    state             LowCardinality(String),
    district          LowCardinality(String),
    age_bracket       LowCardinality(String),
    income_bracket    LowCardinality(String),
    gender            LowCardinality(String),
    urban_rural       LowCardinality(String),
    scheme_id         String,
    scheme_category   LowCardinality(String),
    action            Enum8('eligible' = 1, 'applied' = 2, 'approved' = 3, 
                           'rejected' = 4, 'disbursed' = 5, 'lapsed' = 6),
    benefit_amount    Float64,
    confidence_score  Float32,
    source_engine     LowCardinality(String)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (state, district, scheme_id, event_date)
TTL event_date + INTERVAL 5 YEAR;
```

### 4.2 ClickHouse — Regional Aggregates (Materialized View)

```sql
CREATE MATERIALIZED VIEW regional_scheme_stats
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (state, district, scheme_id, event_date)
AS SELECT
    event_date,
    state,
    district,
    scheme_id,
    countIf(action = 'eligible') AS eligible_count,
    countIf(action = 'applied') AS applied_count,
    countIf(action = 'approved') AS approved_count,
    countIf(action = 'disbursed') AS disbursed_count,
    sumIf(benefit_amount, action = 'disbursed') AS total_disbursed,
    avgIf(confidence_score, action = 'eligible') AS avg_confidence,
    count() AS total_events
FROM scheme_adoption_facts
GROUP BY event_date, state, district, scheme_id;
```

### 4.3 TimescaleDB — Platform Metrics

```sql
CREATE TABLE platform_metrics (
    time              TIMESTAMPTZ NOT NULL,
    metric_name       TEXT NOT NULL,
    metric_value      DOUBLE PRECISION NOT NULL,
    dimensions        JSONB,
    source_engine     TEXT
);

SELECT create_hypertable('platform_metrics', 'time');

-- Continuous aggregate for hourly rollups
CREATE MATERIALIZED VIEW platform_metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    metric_name,
    AVG(metric_value) AS avg_value,
    MAX(metric_value) AS max_value,
    MIN(metric_value) AS min_value,
    COUNT(*) AS sample_count
FROM platform_metrics
GROUP BY bucket, metric_name
WITH NO DATA;

SELECT add_continuous_aggregate_policy('platform_metrics_hourly',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

### 4.4 Apache Iceberg — Historical Archive Schema

```json
{
  "schema": {
    "fields": [
      { "id": 1, "name": "snapshot_date", "type": "date", "required": true },
      { "id": 2, "name": "user_id_hash", "type": "string", "required": true },
      { "id": 3, "name": "state", "type": "string", "required": true },
      { "id": 4, "name": "profile_snapshot", "type": "string", "required": true },
      { "id": 5, "name": "eligibility_count", "type": "int", "required": true },
      { "id": 6, "name": "active_schemes_count", "type": "int", "required": true },
      { "id": 7, "name": "total_benefit_inr", "type": "double", "required": false },
      { "id": 8, "name": "completeness_pct", "type": "int", "required": true }
    ]
  },
  "partition_spec": [
    { "field": "snapshot_date", "transform": "month" },
    { "field": "state", "transform": "identity" }
  ]
}
```

---

## 5. Context Flow

```
                    ┌──────────────────────────────┐
                    │       Data Sources            │
                    │                               │
                    │  Profile Snapshots            │
                    │  Eligibility Computations     │
                    │  Scheme Status Changes        │
                    │  Deadline Outcomes            │
                    │  Trust Score Updates          │
                    │  Platform Telemetry           │
                    └──────────────┬────────────────┘
                                   │
                    ┌──────────────▼────────────────┐
                    │      Ingestion Layer          │
                    │                               │
                    │  ┌─────────────────────────┐  │
                    │  │ Stream Processor        │  │
                    │  │ (Kafka → ClickHouse)    │  │
                    │  │                         │  │
                    │  │ • Anonymize user IDs    │  │
                    │  │ • Extract dimensions    │  │
                    │  │ • Validate schema       │  │
                    │  │ • Route to tables       │  │
                    │  └─────────────────────────┘  │
                    │                               │
                    │  ┌─────────────────────────┐  │
                    │  │ Batch Loader            │  │
                    │  │ (Daily → Iceberg)       │  │
                    │  │                         │  │
                    │  │ • Nightly snapshots     │  │
                    │  │ • Partition compaction  │  │
                    │  │ • Historical archive    │  │
                    │  └─────────────────────────┘  │
                    └──────────────┬────────────────┘
                                   │
                    ┌──────────────▼────────────────┐
                    │      Compute Layer            │
                    │                               │
                    │  ┌─────────┐ ┌──────────────┐ │
                    │  │  dbt    │ │ RAPIDS GPU   │ │
                    │  │ Models  │ │ Pipeline     │ │
                    │  │         │ │              │ │
                    │  │ SQL     │ │ cuDF + cuML  │ │
                    │  │ trans-  │ │ XGBoost      │ │
                    │  │ forms   │ │ Impact model │ │
                    │  └─────────┘ └──────────────┘ │
                    └──────────────┬────────────────┘
                                   │
                    ┌──────────────▼────────────────┐
                    │      Data Cube Layer          │
                    │                               │
                    │  Pre-computed aggregates:      │
                    │  • State × Scheme × Month     │
                    │  • District × Demographic     │
                    │  • Cohort × Action × Quarter  │
                    │                               │
                    │  Refresh: Every 15 min        │
                    └──────────────┬────────────────┘
                                   │
                    ┌──────────────▼────────────────┐
                    │      Serving Layer            │
                    │                               │
                    │  • REST API (aggregates)      │
                    │  • GraphQL (flexible queries) │
                    │  • Export API (research)      │
                    │  • Dashboard WebSocket feed   │
                    └──────────────────────────────┘
```

---

## 6. Event Bus Integration

### Consumed Events

| Event | Source | Action |
|---|---|---|
| `profile.snapshot.created` | JSON User Info Generator | Archive to Iceberg, update ClickHouse |
| `eligibility.batch.computed` | Eligibility Rules Engine | Update scheme adoption facts |
| `scheme.application.status_changed` | Gov Data Sync Engine | Track application funnel |
| `deadline.outcome` | Deadline Monitoring Engine | Track compliance rates |
| `trust.score.updated` | Trust Scoring Engine | Update confidence distributions |
| `platform.metric` | All Engines | Ingest into TimescaleDB |

### Published Events

| Event | Payload | Consumers |
|---|---|---|
| `analytics.cube.refreshed` | `{ cube_name, refresh_time, row_count }` | Dashboard Interface |
| `analytics.anomaly.detected` | `{ metric, expected, actual, severity }` | Anomaly Detection Engine |
| `analytics.report.generated` | `{ report_id, type, format }` | Admin Dashboard |
| `analytics.cohort.updated` | `{ cohort_id, user_count, changes }` | JSON User Info Generator |

---

## 7. NVIDIA Stack Alignment

| NVIDIA Tool | Component | Usage |
|---|---|---|
| **RAPIDS cuDF** | Data Transformation | GPU-accelerated DataFrame operations for ETL on millions of rows |
| **RAPIDS cuML** | Impact Modeling | GPU-accelerated XGBoost for scheme impact prediction |
| **RAPIDS cuGraph** | Network Analysis | Graph analytics for scheme interconnection and user flow patterns |
| **TensorRT-LLM** | Report Generation | Generate natural-language analytics summaries for admin dashboards |
| **NIM** | Insight Extraction | Llama 3.1 8B for generating human-readable insights from aggregated data |
| **Triton** | Model Serving | Serve XGBoost impact models for budget effect simulation |

### RAPIDS Impact Modeling Pipeline

```python
import cudf
import cuml
from cuml.ensemble import RandomForestClassifier
from xgboost import XGBRegressor
import cupy as cp

def train_impact_model(adoption_data_path: str):
    """Train scheme impact model using RAPIDS GPU acceleration."""
    
    # Load data on GPU
    gdf = cudf.read_parquet(adoption_data_path)
    
    # Feature engineering on GPU
    features = gdf[['age_bracket_encoded', 'income_bracket_encoded',
                     'state_encoded', 'urban_rural_encoded',
                     'scheme_category_encoded', 'months_enrolled']]
    
    target = gdf['benefit_realized_pct']  # 0-100% of max benefit
    
    # Train XGBoost on GPU
    model = XGBRegressor(
        tree_method='gpu_hist',
        n_estimators=500,
        max_depth=8,
        learning_rate=0.05,
        gpu_id=0
    )
    model.fit(features, target)
    
    return model

def predict_budget_impact(model, scenario_df: cudf.DataFrame):
    """Predict budget impact of policy changes."""
    predictions = model.predict(scenario_df)
    total_impact = predictions.sum()
    return {
        'total_beneficiaries': len(scenario_df),
        'avg_benefit_realization': float(predictions.mean()),
        'total_budget_impact_inr': float(total_impact),
        'p95_individual_benefit': float(cp.percentile(predictions, 95))
    }
```

---

## 8. Scaling Strategy

| Tier | Users | Strategy |
|---|---|---|
| **MVP** | < 10K | Single ClickHouse node, PostgreSQL+TimescaleDB, daily dbt runs |
| **Growth** | 10K–500K | ClickHouse cluster (3 shards), hourly cube refresh, RAPIDS on single GPU |
| **Scale** | 500K–5M | ClickHouse ReplicatedMergeTree (6 nodes), Apache Iceberg on S3, RAPIDS multi-GPU (DGX A100) |
| **Massive** | 5M–50M+ | ClickHouse distributed cluster (12+ nodes), Iceberg with Spark for heavy ETL, RAPIDS multi-node, materialized views with auto-refresh |

### Data Retention Policy

| Data Type | Hot (ClickHouse) | Warm (Iceberg/S3) | Cold (Glacier) |
|---|---|---|---|
| Raw events | 90 days | 2 years | 7 years |
| Aggregated cubes | 1 year | 5 years | Indefinite |
| Platform metrics | 30 days | 1 year | 3 years |
| Research exports | N/A | 1 year | 5 years |

---

## 9. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/analytics/schemes/{scheme_id}/adoption` | Scheme adoption metrics by region |
| `GET` | `/api/v1/analytics/regions/{state}/heatmap` | Regional heatmap data |
| `GET` | `/api/v1/analytics/cohorts/{cohort_id}/metrics` | Cohort-level analytics |
| `GET` | `/api/v1/analytics/impact/{scheme_id}/prediction` | Impact prediction for scheme |
| `POST` | `/api/v1/analytics/budget/simulate` | Budget impact simulation |
| `GET` | `/api/v1/analytics/platform/health` | Platform health metrics |
| `GET` | `/api/v1/analytics/trends/{metric}` | Time-series trend data |
| `POST` | `/api/v1/analytics/export/research` | Generate anonymized research export |
| `POST` | `/api/v1/analytics/query` | Ad-hoc SQL query (admin only) |

### Example — Scheme Adoption Heatmap

```json
GET /api/v1/analytics/schemes/pm_kisan/adoption?level=district&state=karnataka

{
  "scheme_id": "pm_kisan",
  "state": "karnataka",
  "level": "district",
  "period": "2025-Q1",
  "districts": [
    {
      "district": "bengaluru_urban",
      "eligible": 125000,
      "applied": 45000,
      "approved": 38000,
      "adoption_rate": 0.304,
      "avg_benefit_inr": 6000,
      "trend": "increasing"
    },
    {
      "district": "mysuru",
      "eligible": 89000,
      "applied": 62000,
      "approved": 55000,
      "adoption_rate": 0.618,
      "avg_benefit_inr": 6000,
      "trend": "stable"
    }
  ],
  "_meta": {
    "computed_at": "2025-01-15T10:00:00Z",
    "data_freshness_hours": 1.5
  }
}
```

---

## 10. Dependencies

### Upstream (Data Sources)

| Engine | Data Provided |
|---|---|
| JSON User Info Generator | Profile snapshots (anonymized) |
| Eligibility Rules Engine | Eligibility computation results |
| Deadline Monitoring Engine | Deadline compliance outcomes |
| Government Data Sync Engine | Scheme metadata, budget allocations |
| Trust Scoring Engine | Confidence distributions |
| All Engines | Platform telemetry/metrics |

### Downstream (Consumers)

| Engine | Data Consumed |
|---|---|
| Dashboard Interface | Pre-computed data cubes, heatmap data |
| Simulation Engine | Historical baselines for "what-if" modeling |
| JSON User Info Generator | Cohort tags and aggregated metrics |
| Neural Network Engine | Population-level context for AI reasoning |
| Admin Console | Platform health, scheme performance |

---

## 11. Technology Stack

| Component | Technology |
|---|---|
| OLAP Database | ClickHouse 24.x |
| Time-Series DB | TimescaleDB (PostgreSQL extension) |
| Data Lake | Apache Iceberg + S3/MinIO |
| File Format | Parquet (columnar) |
| ETL Framework | dbt (SQL transforms) |
| GPU Compute | RAPIDS cuDF / cuML / XGBoost |
| Streaming Ingestion | Kafka Connect + ClickHouse Kafka Engine |
| Query API | FastAPI (Python) |
| Visualization API | GraphQL (Strawberry) |
| Monitoring | Prometheus + Grafana |
| Scheduling | Apache Airflow (DAG orchestration) |

---

## 12. Implementation Phases

### Phase 1 — Foundation (Weeks 1-2)
- Set up ClickHouse single-node with scheme adoption fact table
- Kafka consumer for profile and eligibility events
- Basic anonymization pipeline (hash user IDs)
- TimescaleDB for platform metrics

### Phase 2 — Compute Layer (Weeks 3-4)
- dbt models for regional aggregates and materialized views
- Data cube generation (state × scheme × month)
- REST API for serving pre-computed analytics
- Apache Iceberg table for historical archiving

### Phase 3 — GPU Analytics (Weeks 5-6)
- RAPIDS cuDF ETL pipeline for batch transformations
- XGBoost impact model training pipeline
- Budget simulation API endpoint
- Cohort analysis engine

### Phase 4 — Scale & Intelligence (Weeks 7-8)
- ClickHouse clustering (3 shards + replication)
- Real-time cube refresh (15-minute intervals)
- k-anonymity export pipeline for research
- NIM-powered natural-language insight generation
- Grafana dashboards for platform health

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Cube query latency (p50) | < 100ms |
| Cube query latency (p99) | < 500ms |
| Data freshness (event to queryable) | < 15 minutes |
| Cube refresh interval | 15 minutes |
| ClickHouse insert throughput | > 100K events/sec |
| Impact model prediction latency | < 200ms |
| Research export generation time | < 5 minutes (1M rows) |
| Data retention compliance | 100% |
| k-anonymity guarantee (research exports) | k ≥ 10 |
| GPU utilization (RAPIDS pipeline) | > 70% during batch jobs |

---

## 14. Official Data Sources — Analytics & Heatmaps (MVP)

| Data Required | Official Source | URL | Notes |
|---|---|---|---|
| District-level data, CSV datasets | Open Government Data Portal | https://data.gov.in | Granular district-wise scheme data |
| Rural/urban classification, geographic data | Census India | https://censusindia.gov.in | District boundaries, population density |
| Development indicators, policy indices | NITI Aayog | https://www.niti.gov.in | SDG India Index, Aspirational Districts rankings |
| Socio-economic structured datasets | NDAP (NITI Aayog) | https://ndap.niti.gov.in | Clean, API-accessible datasets |

### Optional Future — Global Comparative Data

| Data | Source | URL | Notes |
|---|---|---|---|
| Global economic indicators | World Bank | https://data.worldbank.org | Open data, country-level |
| IMF datasets | IMF Data | https://data.imf.org | Free macroeconomic data |
| UN development data | UN Data | https://data.un.org | SDG, HDI, population |

### Usage in Analytics Warehouse

- **data.gov.in** → Scheme adoption facts at district granularity
- **Census India** → Geographic base layer for heatmaps
- **NITI Aayog** → Benchmark indices for impact correlation
- **World Bank/IMF** → Cross-country comparison for policy effectiveness research

---

## 14. Security Hardening

### 14.1 Rate Limiting

<!-- SECURITY: Analytics queries can be very expensive (ClickHouse full scans).
     Rate limits prevent query abuse and cost explosion.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  # SECURITY: Ad-hoc analytics query — potentially expensive
  "/api/v1/analytics/query":
    per_user:
      requests_per_minute: 10
      burst: 3
    per_ip:
      requests_per_minute: 5

  # SECURITY: Pre-built dashboard metrics — cached, cheaper
  "/api/v1/analytics/dashboards/{dashboard_id}":
    per_user:
      requests_per_minute: 30
      burst: 10

  # SECURITY: Data export — admin only, large payloads
  "/api/v1/analytics/export":
    per_user:
      requests_per_hour: 5
    require_role: admin
    max_export_rows: 100000

  # SECURITY: Funnel/cohort analysis — heavy aggregation
  "/api/v1/analytics/funnel":
    per_user:
      requests_per_minute: 5
      burst: 2

  # SECURITY: Query execution limits
  query_guards:
    max_query_duration_seconds: 30   # Kill queries over 30s
    max_memory_per_query_mb: 512     # Memory cap per query
    max_rows_scanned: 10000000       # 10M row scan limit
    max_result_rows: 10000           # Paginate beyond this

  rate_limit_response:
    status: 429
    body:
      error: "rate_limit_exceeded"
      message: "Analytics query rate limit reached. Please wait before running another query."
```

### 14.2 Input Validation & Sanitization

<!-- SECURITY: Analytics accepts structured queries — prevent SQL injection,
     data exfiltration, and resource exhaustion.
     OWASP Reference: API3:2023, API8:2023 -->

```python
# SECURITY: Analytics query schema — parameterized queries only
ANALYTICS_QUERY_SCHEMA = {
    "type": "object",
    "required": ["query_type"],
    "additionalProperties": False,
    "properties": {
        "query_type": {
            "type": "string",
            "enum": ["funnel", "cohort", "time_series", "distribution", "top_n", "comparison"]
        },
        "metrics": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "string",
                "enum": ["page_views", "scheme_checks", "eligibility_runs",
                         "simulations", "voice_sessions", "registrations",
                         "active_users", "trust_scores", "response_latency"]
            }
        },
        "dimensions": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "string",
                "enum": ["state", "district", "category", "scheme_type",
                         "language", "device_type", "time_bucket"]
            }
        },
        "filters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "date_from": {"type": "string", "format": "date"},
                "date_to": {"type": "string", "format": "date"},
                "state": {"type": "string", "maxLength": 50},
                "scheme_id": {"type": "string", "pattern": "^sch_[a-zA-Z0-9]+$"}
            }
        },
        "limit": {"type": "integer", "minimum": 1, "maximum": 10000}
    }
}

# SECURITY: No raw SQL accepted from users — all queries built server-side
# from validated parameters using parameterized ClickHouse queries.
# Raw SQL is ONLY accepted from admin users via internal pgAdmin-equivalent tool.
RAW_SQL_POLICY = {
    "user_facing_endpoints": "NEVER accept raw SQL",
    "admin_tool": "Parameterized queries only; executed as read-only ClickHouse user",
    "row_level_security": "Analytics data is pre-aggregated; no PII in warehouse"
}
```

### 14.3 Secure API Key & Secret Management

```yaml
secrets_management:
  environment_variables:
    - CLICKHOUSE_PASSWORD       # ClickHouse analytics DB
    - TIMESCALE_PASSWORD        # TimescaleDB time-series
    - S3_ACCESS_KEY_ID          # Iceberg table storage
    - S3_SECRET_ACCESS_KEY      # Iceberg table storage
    - KAFKA_SASL_PASSWORD       # Event bus auth
    - REDIS_PASSWORD            # Query result cache
    - GRAFANA_ADMIN_PASSWORD    # Monitoring dashboard

  rotation_policy:
    db_credentials: 90_days
    s3_credentials: 90_days
    grafana_password: 90_days

  # SECURITY: Analytics data is anonymized — no PII
  data_policy:
    no_pii_in_warehouse: true
    user_ids_hashed: true         # SHA-256 hashed user IDs only
    ip_addresses_anonymized: true # Last octet zeroed
    retention_days: 365
```

### 14.4 OWASP Compliance

| OWASP Risk | Mitigation |
|---|---|
| **API1: BOLA** | Analytics data is aggregated — no user-level data exposed; admin scoping for exports |
| **API2: Broken Auth** | JWT validation; export endpoints require admin role |
| **API3: Broken Property Auth** | Query schema with metric/dimension enums; no arbitrary columns |
| **API4: Resource Consumption** | Query duration limits, memory caps, row scan limits, result pagination |
| **API5: Broken Function Auth** | Export/admin queries restricted to admin role |
| **API6: Sensitive Flows** | No PII in warehouse; user IDs hashed |
| **API7: SSRF** | No external URL inputs; all data ingested via Kafka |
| **API8: Misconfig** | ClickHouse read-only user for analytics; no DDL via API |
| **API9: Improper Inventory** | Query templates versioned; deprecated metrics flagged |
| **API10: Unsafe Consumption** | Kafka event payloads validated against schema before insertion |

---

## ⚙️ Build Phase Instructions (Current Phase Override)

> **These instructions override any conflicting guidance above for the current local build phase.**

### 1. Local-First Architecture
- Build and run this engine **entirely locally**. Do NOT integrate any AWS cloud services.
- **Replace S3/Glacier with local filesystem** or MinIO (local Docker) for any object storage needs.
- Use ClickHouse running locally (Docker) for OLAP analytics.
- Store all secrets in a local `.env` file. Do NOT use AWS Secrets Manager.
- Apache Iceberg → Use local filesystem-backed Iceberg tables if needed, or defer Iceberg entirely.

### 2. Data Storage & Caching (Zero-Redundancy)
- Before downloading or fetching any external data/files, **always check if the target data already exists locally**.
- If present locally → skip the download and load directly from the local path.
- Only download/fetch data if it is **completely missing locally**.
- **Local datasets available** (use these instead of API calls):
  - Finance/economic data: `C:\Users\Amandeep\Downloads\financefiles\` (18 Excel files covering GDP, CPI, WPI, wages, reserves, market indices, etc.)
  - Census 2011 data: `C:\Users\Amandeep\Downloads\DDW_PCA0000_2011_Indiastatedist.xlsx`
  - SDG India Index: `C:\Users\Amandeep\Downloads\amandeepsinghchauhan5_17722109276149728.csv`
  - NFHS-5 district data: `C:\Users\Amandeep\Downloads\NFHS 5 district wise data\NFHS 5 district wise data\ssrn datasheet.xls`
  - Poverty data: `C:\Users\Amandeep\Downloads\amandeepsinghchauhan5_17722114987588584.csv`
  - Aspirational Districts: `C:\Users\Amandeep\Downloads\List-of-112-Aspirational-Districts (1).pdf`

### 3. Deferred Features (Do NOT Implement Yet)
- **Notifications & Messaging**: Do not build or integrate any notification systems.
- **Cloud storage tiering**: Use local filesystem only.

### 4. Primary Focus
Build a robust, locally-functioning analytics warehouse with:
- ClickHouse (local) for OLAP queries
- Kafka event ingestion for analytics data
- Pre-built analytics dashboards using local data
- Heatmap and impact modeling using locally available datasets
- All functionality testable without any external service or cloud dependencies
