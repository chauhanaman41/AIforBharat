# 🟦 Raw Data Store — Design & Plan

## 1. Purpose

The Raw Data Store is the **immutable compliance and audit backbone** of the AIforBharat platform. It captures every user interaction, system event, policy snapshot, and historical government data in an **append-only architecture** ensuring nothing is ever lost or tampered with.

This store serves as the authoritative source for:
- Regulatory compliance and audit trails
- Historical data replay and debugging
- Training data for ML model improvement
- Legal evidence in case of disputes

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Immutable Event Logs** | Append-only storage — no updates or deletes |
| **User Activity Tracking** | Every user action logged with context |
| **Policy Snapshots** | Point-in-time captures of policy data |
| **Historical Government Data** | Archived versions of schemes, budgets, gazette notifications |
| **Audit Trail** | Who accessed what, when, and why |
| **Time-Series Logging** | Ordered event streams for replay and analysis |
| **Compliance Backbone** | DPDP Act, RTI compliance data retention |
| **Data Replay** | Replay events for debugging or model retraining |
| **Tamper Detection** | Hash chains for integrity verification |
| **Partitioned Storage** | Efficient querying by user_id, date, region |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              All Platform Engines (Event Producers)          │
│                                                             │
│  Login Engine │ Identity Engine │ AI Core │ Policy Fetcher  │
│  Metadata Engine │ Anomaly Detection │ Dashboard │ ...      │
└────────────────────────────┬────────────────────────────────┘
                             │ Events via Kafka / NATS
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     Raw Data Store                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Ingestion Pipeline                       │   │
│  │                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │   │
│  │  │ Event        │  │ Schema       │  │ Hash      │  │   │
│  │  │ Validator    │  │ Enforcer     │  │ Generator │  │   │
│  │  └──────────────┘  └──────────────┘  └───────────┘  │   │
│  └──────────────────────────┬───────────────────────────┘   │
│                             │                               │
│  ┌──────────────────────────▼───────────────────────────┐   │
│  │              Storage Tiers                            │   │
│  │                                                      │   │
│  │  ┌──────────────────┐  ┌──────────────────────────┐  │   │
│  │  │  Hot Tier         │  │  Warm Tier               │  │   │
│  │  │  (0-30 days)      │  │  (30-365 days)           │  │   │
│  │  │  S3 Standard /    │  │  S3 Infrequent Access /  │  │   │
│  │  │  MinIO             │  │  GCS Nearline            │  │   │
│  │  └──────────────────┘  └──────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────┐  ┌──────────────────────────┐  │   │
│  │  │  Cold Tier        │  │  Time-Series Index       │  │   │
│  │  │  (365+ days)      │  │  (ClickHouse /           │  │   │
│  │  │  S3 Glacier /     │  │   TimescaleDB)           │  │   │
│  │  │  Archive          │  │                          │  │   │
│  │  └──────────────────┘  └──────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Query Layer                              │   │
│  │                                                      │   │
│  │  • By user_id    • By date range    • By region      │   │
│  │  • By event_type • By engine_source • Full-text      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Append-Only Guarantee

- **No UPDATE or DELETE operations** allowed on raw data
- Every record gets a **SHA-256 hash** including the previous record's hash (hash chain)
- Tamper detection runs as a **background audit job** every 6 hours
- Storage layer enforced via **S3 Object Lock** (WORM compliance)

---

## 4. Data Models

### 4.1 Raw Event Record

```json
{
  "event_id": "evt_uuid_v4",
  "event_type": "USER_ACTION",
  "event_subtype": "SCHEME_SEARCH",
  "source_engine": "neural-network-engine",
  "user_id": "usr_uuid_v4",
  "identity_token": "idt_a1b2c3d4",
  "timestamp": "2026-02-26T10:05:00.123Z",
  "region": "UP",
  "payload": {
    "query": "PM Kisan eligibility",
    "results_count": 5,
    "response_time_ms": 230
  },
  "metadata": {
    "session_id": "sess_uuid",
    "device_type": "mobile",
    "app_version": "1.2.0",
    "ip_hash": "sha256_hash"
  },
  "hash": "sha256_of_this_record",
  "prev_hash": "sha256_of_previous_record"
}
```

### 4.2 Policy Snapshot Record

```json
{
  "snapshot_id": "snap_uuid_v4",
  "policy_id": "pol_pm_kisan_v3",
  "version": 3,
  "snapshot_type": "FULL",
  "captured_at": "2026-02-26T00:00:00Z",
  "source": "gazette_notification",
  "content_hash": "sha256_of_policy_content",
  "storage_path": "s3://raw-data/policies/2026/02/pol_pm_kisan_v3.json",
  "metadata": {
    "effective_date": "2026-04-01",
    "ministry": "Agriculture",
    "state": "CENTRAL",
    "amendment_ref": "GOI/2026/AGR/1234"
  }
}
```

### 4.3 Partitioning Scheme

```
s3://aifor-bharat-raw-data/
├── events/
│   ├── region=UP/
│   │   ├── year=2026/
│   │   │   ├── month=02/
│   │   │   │   ├── day=26/
│   │   │   │   │   ├── hour=10/
│   │   │   │   │   │   ├── events_001.parquet
│   │   │   │   │   │   └── events_002.parquet
├── policies/
│   ├── ministry=agriculture/
│   │   ├── year=2026/
│   │   │   ├── pol_pm_kisan_v3.json
├── audit/
│   ├── year=2026/
│   │   ├── month=02/
│   │   │   ├── identity_access_log.parquet
```

---

## 5. Context Flow

```
Event arrives from Event Bus (Kafka / NATS)
    │
    ├─► Ingestion Pipeline receives event
    │       │
    │       ├─► Validate schema against registered event types
    │       ├─► Generate SHA-256 hash (including prev_hash for chain)
    │       ├─► Enrich with metadata (timestamp normalization, region tagging)
    │       ├─► Determine storage tier (Hot by default)
    │       ├─► Write to object storage (S3/MinIO) in Parquet format
    │       ├─► Index in time-series DB (ClickHouse/TimescaleDB)
    │       └─► Acknowledge event consumption
    │
    ├─► [Policy Snapshot] → Triggered by Government Data Sync Engine
    │       │
    │       ├─► Capture full policy content
    │       ├─► Hash content for integrity
    │       ├─► Store in policies partition
    │       └─► Index in metadata catalog
    │
    └─► [Tier Migration] → Background job
            │
            ├─► Hot → Warm after 30 days (compress, move to IA storage)
            ├─► Warm → Cold after 365 days (archive to Glacier)
            └─► Verify hash chain integrity on migration
```

---

## 6. Event Bus Integration

| Event Consumed | Source | Action |
|---|---|---|
| `USER_REGISTERED` | Login Engine | Store registration event |
| `LOGIN_SUCCESS/FAILED` | Login Engine | Store auth event |
| `IDENTITY_CREATED` | Identity Engine | Store identity creation event |
| `SCHEME_SEARCHED` | AI Core | Store search query + results |
| `ELIGIBILITY_CHECKED` | Rules Engine | Store eligibility result |
| `POLICY_UPDATED` | Gov Data Sync | Create policy snapshot |
| `ANOMALY_DETECTED` | Anomaly Engine | Store anomaly alert |
| `*` (wildcard) | All Engines | Store any system event |

| Event Published | Consumers |
|---|---|
| `RAW_DATA_STORED` | Analytics Warehouse (for aggregation) |
| `INTEGRITY_VIOLATION` | Anomaly Detection, Admin Dashboard |

---

## 7. NVIDIA Stack Alignment

| Component | NVIDIA Tool | Usage |
|---|---|---|
| High-throughput ingestion | NVIDIA RAPIDS cuDF | GPU-accelerated Parquet writes |
| Data compression | RAPIDS | GPU-accelerated compression for cold tier |
| Integrity verification | CUDA | Parallel hash computation for chain validation |
| Analytics queries | RAPIDS + BlazingSQL | GPU-accelerated SQL on Parquet files |

---

## 8. Scaling Strategy

| Scale Tier | Events/Day | Strategy |
|---|---|---|
| **Tier 1** (MVP) | < 100K | Single MinIO instance, TimescaleDB |
| **Tier 2** | 100K – 10M | S3 + ClickHouse, Kafka consumer groups |
| **Tier 3** | 10M – 1B | S3 with partitioned Parquet, ClickHouse cluster |
| **Tier 4** | 1B+ | Multi-region S3, Iceberg table format, GPU-accelerated queries |

### Key Scaling Decisions

- **Partition by**: `region` → `year` → `month` → `day` → `hour`
- **File format**: Apache Parquet (columnar, compressed)
- **Table format**: Apache Iceberg (schema evolution, time travel)
- **Ingestion**: Kafka consumer groups with exactly-once semantics
- **Retention**: Hot (30d) → Warm (365d) → Cold (7 years) → Archive (permanent for policies)

---

## 9. Security & Compliance

| Concern | Implementation |
|---|---|
| **Immutability** | S3 Object Lock (Governance/Compliance mode) |
| **Encryption at rest** | S3 SSE-KMS (AWS) or AES-256 (MinIO) |
| **Encryption in transit** | TLS 1.3 for all data movement |
| **Access control** | IAM policies, no direct S3 access from application |
| **Audit of audits** | Meta-audit log tracking who accessed raw data |
| **DPDP compliance** | PII fields encrypted before storage |
| **Data sovereignty** | All storage in Indian data centers |
| **Retention policy** | Configurable per event type; policy data permanent |

---

## 10. API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/raw-data/events` | Ingest event (internal only) |
| `GET` | `/api/v1/raw-data/events` | Query events (filtered) |
| `GET` | `/api/v1/raw-data/events/{event_id}` | Get specific event |
| `GET` | `/api/v1/raw-data/policies/{policy_id}/history` | Get policy snapshot history |
| `GET` | `/api/v1/raw-data/user/{user_id}/trail` | Get user's complete audit trail |
| `POST` | `/api/v1/raw-data/integrity/verify` | Trigger hash chain verification |
| `GET` | `/api/v1/raw-data/stats` | Storage statistics and health |

---

## 11. Dependencies

| Dependency | Direction | Purpose |
|---|---|---|
| **Event Bus (Kafka/NATS)** | Upstream | Receives all platform events |
| **All Engines** | Upstream | Every engine publishes events consumed by this store |
| **Analytics Warehouse** | Downstream | Feeds aggregated data for OLAP queries |
| **Anomaly Detection** | Downstream | Integrity violation alerts |
| **KMS** | External | Encryption key management for PII fields |

---

## 12. Technology Stack

| Layer | Technology |
|---|---|
| Object Storage | AWS S3 / MinIO (self-hosted) |
| Table Format | Apache Iceberg |
| File Format | Apache Parquet |
| Time-Series DB | ClickHouse / TimescaleDB |
| Ingestion | Kafka Consumers (Python / Go) |
| Query Engine | ClickHouse SQL / RAPIDS BlazingSQL |
| Integrity | SHA-256 hash chains |
| Compression | Zstandard (zstd) |
| Containerization | Docker + Kubernetes |

---

## 13. Implementation Phases

| Phase | Milestone | Timeline |
|---|---|---|
| **Phase 1** | Event ingestion pipeline, MinIO setup, basic Parquet writes | Week 1-2 |
| **Phase 2** | Partitioning scheme, ClickHouse indexing | Week 3-4 |
| **Phase 3** | Hash chain integrity, tamper detection | Week 5-6 |
| **Phase 4** | Tier migration (Hot → Warm → Cold) | Week 7-8 |
| **Phase 5** | Policy snapshot system, query API | Week 9-10 |
| **Phase 6** | S3 Object Lock, compliance certification | Week 12-14 |

---

## 14. Success Metrics

| Metric | Target |
|---|---|
| Ingestion throughput | > 10K events/sec |
| Ingestion latency (P99) | < 500ms |
| Hash chain verification | 100% pass rate |
| Storage cost efficiency | < $0.01 per 1000 events |
| Query latency (recent data, P95) | < 2 seconds |
| Data durability | 99.999999999% (11 nines) |
| Tier migration success rate | > 99.99% |
