# 🟦 Processed User Metadata Store — Design & Plan

## 1. Purpose

The Processed User Metadata Store is the **encrypted relational database** holding the structured, normalized output of the Metadata Engine. It stores user attributes, derived attributes, risk scores, and policy eligibility flags — the **"processed truth"** about each user that drives all downstream intelligence.

This is the store that engines query when they need to answer: *"What do we know about this user right now?"*

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Encrypted Relational Storage** | Row-level encryption for all PII fields |
| **User Attributes** | Primary demographics, economics, family structure |
| **Derived Attributes** | Computed fields: life stage, income bracket, age group |
| **Risk Scores** | Financial risk, deadline risk, benefit loss risk |
| **Policy Eligibility Cache** | Pre-computed eligibility results per user |
| **Read Replicas** | Separate replicas for analytics queries |
| **Temporal Queries** | Query user state at any point in time |
| **Sharded Architecture** | Horizontal partitioning by region |
| **ACID Transactions** | Full transactional consistency for writes |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Write Path                                │
│                                                              │
│  Metadata Engine → Event Bus → Write Workers → Primary DB    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Read Path                                 │
│                                                              │
│  AI Core ─────────┐                                          │
│  Eligibility Engine┤                                         │
│  JSON Generator ──┤──► Read Replicas ──► Response            │
│  Dashboard ───────┤                                          │
│  Analytics ───────┘                                          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              Processed User Metadata Store                    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │            PostgreSQL Cluster                        │     │
│  │                                                     │     │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │     │
│  │  │ Primary     │  │ Read Replica │  │ Read      │  │     │
│  │  │ (Writes)    │  │ #1 (AI/Rules)│  │ Replica #2│  │     │
│  │  │             │  │              │  │ (Analytics)│  │     │
│  │  └──────┬──────┘  └──────────────┘  └───────────┘  │     │
│  │         │                                           │     │
│  │  ┌──────▼──────────────────────────────────────┐    │     │
│  │  │  Citus Distributed Tables                    │    │     │
│  │  │  Shard Key: region (state code)              │    │     │
│  │  │                                              │    │     │
│  │  │  Shard UP │ Shard MH │ Shard KA │ Shard TN  │    │     │
│  │  └─────────────────────────────────────────────┘    │     │
│  │                                                     │     │
│  │  ┌──────────────────────────────────────────────┐   │     │
│  │  │  PgBouncer (Connection Pool)                 │   │     │
│  │  │  Max connections: 500                        │   │     │
│  │  └──────────────────────────────────────────────┘   │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  Encryption Layer                                    │     │
│  │                                                     │     │
│  │  • Column-level: pgcrypto (PII fields)              │     │
│  │  • Row-level: Application-layer AES-256             │     │
│  │  • TDE: Transparent Data Encryption (disk)          │     │
│  │  • Key source: KMS/HSM                              │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Data Models

### 4.1 Core Schema

```sql
-- User Primary Metadata
CREATE TABLE user_metadata (
    metadata_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL,
    identity_token    VARCHAR(64) NOT NULL,
    schema_version    VARCHAR(16) NOT NULL,
    region            VARCHAR(4) NOT NULL,     -- Shard key
    
    -- Primary Attributes (encrypted where PII)
    age               INTEGER,
    date_of_birth     DATE,
    gender            VARCHAR(16),
    marital_status    VARCHAR(16),
    state             VARCHAR(4) NOT NULL,
    district          VARCHAR(64),
    pincode           VARCHAR(6),
    residence_type    VARCHAR(16),
    
    -- Economic Attributes
    annual_income     INTEGER,
    income_source     VARCHAR(32),
    employer_type     VARCHAR(32),
    has_bank_account  BOOLEAN DEFAULT FALSE,
    land_holding      DECIMAL(10,2),
    ration_card_type  VARCHAR(8),
    
    -- Family Attributes
    dependents_count  INTEGER DEFAULT 0,
    children_count    INTEGER DEFAULT 0,
    family_size       INTEGER DEFAULT 1,
    
    -- Timestamps
    created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_user UNIQUE (user_id)
) PARTITION BY LIST (region);

-- Partitions per state
CREATE TABLE user_metadata_up PARTITION OF user_metadata FOR VALUES IN ('UP');
CREATE TABLE user_metadata_mh PARTITION OF user_metadata FOR VALUES IN ('MH');
CREATE TABLE user_metadata_ka PARTITION OF user_metadata FOR VALUES IN ('KA');
-- ... 28 states + 8 UTs

-- Derived Attributes (computed, separate table for flexibility)
CREATE TABLE user_derived_attributes (
    user_id           UUID PRIMARY KEY REFERENCES user_metadata(user_id),
    age_group         VARCHAR(16),        -- child/youth/adult/senior
    income_bracket    VARCHAR(8),         -- BPL/LIG/MIG/HIG
    life_stage        VARCHAR(32),        -- student/early_career/young_family/...
    employment_cat    VARCHAR(32),
    region_code       VARCHAR(16),
    bpl_status        BOOLEAN,
    tax_bracket       VARCHAR(8),
    social_category   VARCHAR(16),
    computed_at       TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Risk Scores (updated by AI engines)
CREATE TABLE user_risk_scores (
    user_id            UUID PRIMARY KEY REFERENCES user_metadata(user_id),
    financial_risk     DECIMAL(3,2),      -- 0.00 to 1.00
    deadline_risk      DECIMAL(3,2),
    benefit_loss_risk  DECIMAL(3,2),
    overall_risk       DECIMAL(3,2),
    model_version      VARCHAR(16),
    computed_at        TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Eligibility Cache
CREATE TABLE user_eligibility_cache (
    user_id    UUID NOT NULL REFERENCES user_metadata(user_id),
    scheme_id  VARCHAR(64) NOT NULL,
    eligible   BOOLEAN NOT NULL,
    score      DECIMAL(3,2),
    reasons    JSONB,
    computed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, scheme_id)
);

-- Metadata History (append-only for temporal queries)
CREATE TABLE user_metadata_history (
    history_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL,
    changed_fields JSONB NOT NULL,
    old_values    JSONB NOT NULL,
    new_values    JSONB NOT NULL,
    changed_by    VARCHAR(64) NOT NULL,
    changed_at    TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 4.2 Indexes

```sql
-- Performance-critical indexes
CREATE INDEX idx_metadata_region ON user_metadata(region);
CREATE INDEX idx_metadata_state_age ON user_metadata(state, age);
CREATE INDEX idx_metadata_income ON user_metadata(annual_income);
CREATE INDEX idx_derived_life_stage ON user_derived_attributes(life_stage);
CREATE INDEX idx_derived_income_bracket ON user_derived_attributes(income_bracket);
CREATE INDEX idx_eligibility_scheme ON user_eligibility_cache(scheme_id);
CREATE INDEX idx_eligibility_expiry ON user_eligibility_cache(expires_at);
CREATE INDEX idx_risk_overall ON user_risk_scores(overall_risk DESC);
CREATE INDEX idx_history_user_time ON user_metadata_history(user_id, changed_at DESC);
```

---

## 5. Context Flow

```
Metadata Engine publishes METADATA_UPDATED event
    │
    ├─► Write Worker receives event
    │       │
    │       ├─► Decrypt any PII fields using KMS key
    │       ├─► Begin transaction
    │       ├─► UPSERT into user_metadata
    │       ├─► Recompute derived attributes
    │       ├─► UPSERT into user_derived_attributes
    │       ├─► INSERT into user_metadata_history
    │       ├─► Invalidate eligibility cache for this user
    │       ├─► Commit transaction
    │       └─► Publish METADATA_STORED event
    │
    ├─► Read path (AI Core / Rules Engine / Dashboard)
    │       │
    │       ├─► Query via read replica (route by purpose)
    │       ├─► Decrypt PII on-the-fly if authorized
    │       └─► Return metadata with schema version
    │
    └─► Analytics path
            │
            ├─► Query via analytics read replica
            ├─► Data returned anonymized (no PII decryption)
            └─► Aggregated results only
```

---

## 6. Event Bus Integration

| Event Consumed | Source | Action |
|---|---|---|
| `METADATA_CREATED` | Metadata Engine | Insert new user record |
| `METADATA_UPDATED` | Metadata Engine | Update existing record, log history |
| `RISK_SCORES_COMPUTED` | AI Core | Update risk scores table |
| `ELIGIBILITY_COMPUTED` | Rules Engine | Update eligibility cache |

| Event Published | Consumers |
|---|---|
| `METADATA_STORED` | JSON User Info Generator, AI Core |
| `ELIGIBILITY_CACHE_INVALIDATED` | Eligibility Rules Engine |

---

## 7. NVIDIA Stack Alignment

| Component | NVIDIA Tool | Usage |
|---|---|---|
| Bulk data processing | RAPIDS cuDF | GPU-accelerated batch inserts/updates |
| Analytics queries | RAPIDS + BlazingSQL | GPU-accelerated aggregations on read replicas |
| Encryption acceleration | NVIDIA GPU crypto | Hardware-accelerated AES for row-level encryption |

---

## 8. Scaling Strategy

| Scale Tier | Users | Strategy |
|---|---|---|
| **Tier 1** (MVP) | < 10K | Single PostgreSQL, no sharding |
| **Tier 2** | 10K – 1M | PostgreSQL + 2 read replicas, PgBouncer |
| **Tier 3** | 1M – 10M | Citus sharding by region, 3+ read replicas |
| **Tier 4** | 10M+ | Multi-region Citus clusters, edge caching, materialized views |

### Key Decisions

- **Shard key**: `region` (state code) — aligns with policy jurisdictions
- **Connection pooling**: PgBouncer with 500 max connections
- **Read replicas**: Separate replicas for AI workloads vs analytics
- **Cache invalidation**: Event-driven; eligibility cache TTL = 24 hours
- **Vacuum strategy**: Aggressive autovacuum for history table

---

## 9. Security

| Concern | Implementation |
|---|---|
| **Row-level encryption** | PII fields encrypted with per-user key via pgcrypto |
| **TDE** | Transparent Data Encryption for disk-level protection |
| **Access control** | PostgreSQL Row-Level Security (RLS) policies |
| **Audit** | Every write logged to history table + Raw Data Store |
| **Network** | TLS 1.3 for all connections, VPC isolation |
| **Backup encryption** | Backups encrypted with separate KMS key |

---

## 10. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/user-metadata/{user_id}` | Get current user metadata |
| `GET` | `/api/v1/user-metadata/{user_id}/derived` | Get derived attributes |
| `GET` | `/api/v1/user-metadata/{user_id}/risk-scores` | Get risk scores |
| `GET` | `/api/v1/user-metadata/{user_id}/eligibility` | Get cached eligibility |
| `GET` | `/api/v1/user-metadata/{user_id}/history` | Get metadata change history |
| `GET` | `/api/v1/user-metadata/query` | Query users by attributes (admin) |
| `GET` | `/api/v1/user-metadata/stats` | Aggregate statistics (anonymized) |

---

## 11. Dependencies

| Dependency | Direction | Purpose |
|---|---|---|
| **Metadata Engine** | Upstream | Writes normalized metadata |
| **AI Core (Neural Network)** | Upstream | Writes risk scores |
| **Eligibility Rules Engine** | Upstream / Downstream | Writes eligibility cache, reads metadata |
| **JSON User Info Generator** | Downstream | Reads complete user profile |
| **Dashboard** | Downstream | Reads user metadata for display |
| **Analytics Warehouse** | Downstream | Reads anonymized aggregates |
| **KMS/HSM** | External | Encryption key management |

---

## 12. Technology Stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL 16 + Citus (distributed) |
| Connection Pooling | PgBouncer |
| Encryption | pgcrypto + application-layer AES-256 |
| ORM | SQLAlchemy 2.0 (async) |
| Migration | Alembic |
| Monitoring | pg_stat_statements, Prometheus postgres_exporter |
| Backup | pg_basebackup + WAL-G (continuous archiving) |
| Containerization | Docker + Kubernetes (StatefulSet) |

---

## 13. Implementation Phases

| Phase | Milestone | Timeline |
|---|---|---|
| **Phase 1** | Core schema, basic CRUD, single PostgreSQL | Week 1-2 |
| **Phase 2** | Derived attributes table, history tracking | Week 3 |
| **Phase 3** | Row-level encryption, KMS integration | Week 4-5 |
| **Phase 4** | Read replicas, PgBouncer setup | Week 6 |
| **Phase 5** | Eligibility cache, risk scores tables | Week 7-8 |
| **Phase 6** | Citus sharding, regional partitioning | Week 10-12 |

---

## 14. Success Metrics

| Metric | Target |
|---|---|
| Write latency (P95) | < 50ms |
| Read latency (P95) | < 20ms |
| Availability | 99.95% |
| Replication lag | < 100ms |
| Eligibility cache hit rate | > 85% |
| Encryption/decryption overhead | < 5ms per field |
