# JSON User Info Generator Engine — Design & Plan

## 1. Purpose

The JSON User Info Generator is the **unified profile assembly engine** that aggregates data from multiple upstream engines (Identity, Metadata, Eligibility Rules, Deadline Monitoring, Analytics, Trust Scoring) into a single, canonical JSON document representing the complete civic profile of a citizen. This document serves as the **single source of truth** consumed by the Dashboard Interface, Neural Network Engine, Simulation Engine, and external API consumers.

Every downstream engine reads from this assembled profile rather than querying multiple stores independently — enforcing consistency, reducing inter-service coupling, and enabling offline-capable client experiences.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Profile Assembly** | Merge identity, metadata, eligibility, deadlines, risk scores, active schemes, and predictions into one JSON |
| **Schema Versioning** | Maintain backward-compatible profile schemas with version negotiation |
| **Incremental Updates** | Detect changed fields and emit delta patches (JSON Patch RFC 6902) instead of full rebuilds |
| **Field-Level Access Control** | Apply consent-aware field masking based on viewer role and user consent grants |
| **Snapshot Management** | Store point-in-time profile snapshots for audit, simulation rollback, and temporal queries |
| **Real-Time Assembly** | Sub-200ms assembly from cached sources for dashboard rendering |
| **Bulk Export** | Generate anonymized, aggregated profile batches for analytics/research |
| **Profile Completeness Scoring** | Calculate a profile_completeness_pct to nudge users toward providing missing data |
| **Life Event Prediction Embedding** | Embed predicted_events from Neural Network Engine output into the profile |

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  JSON User Info Generator                     │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Aggregation  │  │   Schema     │  │  Snapshot        │   │
│  │  Coordinator  │  │   Registry   │  │  Manager         │   │
│  │              │  │              │  │                  │   │
│  │ - Fetch from │  │ - v1, v2...  │  │ - Point-in-time  │   │
│  │   upstream   │  │ - Migration  │  │ - Diff tracking  │   │
│  │ - Merge      │  │ - Validation │  │ - Retention      │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │
│         │                 │                    │              │
│  ┌──────▼─────────────────▼────────────────────▼──────────┐  │
│  │                   Assembly Pipeline                     │  │
│  │                                                         │  │
│  │  Fetch → Validate → Merge → Enrich → Mask → Serialize  │  │
│  └──────────────────────┬──────────────────────────────────┘  │
│                         │                                     │
│  ┌──────────────┐  ┌────▼─────────┐  ┌──────────────────┐   │
│  │  Delta        │  │  Profile     │  │  Access Control  │   │
│  │  Calculator   │  │  Cache       │  │  Layer           │   │
│  │              │  │  (Redis)     │  │                  │   │
│  │ - JSON Patch │  │ - TTL: 5min  │  │ - Consent check  │   │
│  │ - RFC 6902   │  │ - Warm-up    │  │ - Field masking  │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘

Upstream Sources:
  ├── Identity Engine ────────── identity_token, verified_fields
  ├── Processed User Metadata ── demographics, income, location
  ├── Eligibility Rules Engine ─ eligible_schemes[], matched_rules
  ├── Deadline Monitoring ────── upcoming_deadlines[], alerts
  ├── Trust Scoring Engine ───── confidence_score, source_trace
  ├── Neural Network Engine ──── predicted_events[], recommendations
  └── Analytics Warehouse ────── aggregated_metrics, cohort_tags

Downstream Consumers:
  ├── Dashboard Interface ────── Full/partial profile for rendering
  ├── Neural Network Engine ──── Context for AI reasoning
  ├── Simulation Engine ──────── Baseline profile for "what-if"
  └── External API ───────────── Consent-gated profile export
```

---

## 4. Data Models

### 4.1 Canonical User Profile (v2)

```json
{
  "schema_version": "2.0",
  "profile_id": "prof_uuid_v4",
  "identity_token": "tok_hashed",
  "generated_at": "2025-01-15T10:30:00Z",
  "profile_completeness_pct": 82,
  "assembly_latency_ms": 145,

  "identity": {
    "display_name": "Rajesh K.",
    "age_bracket": "30-40",
    "gender": "male",
    "verified_documents": ["aadhaar", "pan"],
    "delegation_active": false
  },

  "demographics": {
    "state": "karnataka",
    "district": "bengaluru_urban",
    "urban_rural": "urban",
    "pincode": "560001",
    "residency_years": 5
  },

  "economic": {
    "income_bracket": "5L-10L",
    "employment_type": "salaried",
    "tax_regime": "new",
    "bpl_status": false,
    "ration_card_type": "APL"
  },

  "family": {
    "marital_status": "married",
    "dependents": 2,
    "senior_citizen_dependents": 1,
    "children_school_age": 1
  },

  "eligibility": {
    "eligible_schemes": [
      {
        "scheme_id": "sch_001",
        "scheme_name": "PM-KISAN",
        "confidence": 0.95,
        "matched_rules": ["rule_land_holding", "rule_income_cap"],
        "application_status": "not_applied",
        "deadline": "2025-03-31"
      }
    ],
    "total_eligible": 12,
    "total_applied": 3,
    "total_active": 2,
    "potential_annual_benefit_inr": 145000
  },

  "deadlines": {
    "upcoming": [
      {
        "type": "tax_filing",
        "description": "ITR filing deadline",
        "due_date": "2025-07-31",
        "days_remaining": 197,
        "priority": "high",
        "action_url": "/tax/file"
      }
    ],
    "overdue": [],
    "completed_last_90d": 2
  },

  "risk_scores": {
    "deadline_miss_risk": 0.15,
    "benefit_lapse_risk": 0.08,
    "tax_penalty_risk": 0.05,
    "document_expiry_risk": 0.20
  },

  "predictions": {
    "predicted_events": [
      {
        "event": "child_school_admission",
        "estimated_date": "2025-06-01",
        "related_schemes": ["sch_education_001"],
        "confidence": 0.78
      }
    ],
    "recommended_actions": [
      {
        "action": "apply_scheme",
        "scheme_id": "sch_001",
        "reason": "High eligibility match, approaching deadline",
        "priority": 1
      }
    ]
  },

  "trust": {
    "overall_confidence": "high",
    "data_freshness_hours": 2.5,
    "source_trace": {
      "identity": "verified_2025-01-10",
      "schemes": "synced_2025-01-15",
      "deadlines": "computed_2025-01-15"
    }
  },

  "cohort_tags": ["urban_professional", "young_family", "tax_compliant"],

  "consent": {
    "data_sharing_level": "standard",
    "analytics_opt_in": true,
    "third_party_sharing": false,
    "consent_updated_at": "2025-01-01T00:00:00Z"
  }
}
```

### 4.2 Profile Delta Patch (RFC 6902)

```json
{
  "profile_id": "prof_uuid_v4",
  "patch_id": "patch_uuid_v4",
  "base_version": "snap_2025-01-14",
  "generated_at": "2025-01-15T10:30:00Z",
  "operations": [
    { "op": "replace", "path": "/eligibility/total_eligible", "value": 12 },
    { "op": "add", "path": "/deadlines/upcoming/-", "value": { "type": "renewal", "due_date": "2025-04-15" } },
    { "op": "replace", "path": "/profile_completeness_pct", "value": 82 }
  ]
}
```

### 4.3 Profile Snapshot Table (PostgreSQL)

```sql
CREATE TABLE profile_snapshots (
    snapshot_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL,
    schema_version    VARCHAR(10) NOT NULL,
    profile_json      JSONB NOT NULL,
    profile_hash      VARCHAR(64) NOT NULL,  -- SHA-256 of serialized JSON
    completeness_pct  SMALLINT NOT NULL,
    assembly_latency_ms INTEGER NOT NULL,
    source_versions   JSONB NOT NULL,  -- { "identity": "v3", "eligibility": "v12" }
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at        TIMESTAMPTZ,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
) PARTITION BY RANGE (created_at);

-- Monthly partitions
CREATE TABLE profile_snapshots_2025_01 PARTITION OF profile_snapshots
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE INDEX idx_snapshot_user_time ON profile_snapshots (user_id, created_at DESC);
CREATE INDEX idx_snapshot_hash ON profile_snapshots (profile_hash);
```

---

## 5. Context Flow

```
Event Triggers:
  user.metadata.updated  ──┐
  eligibility.computed   ──┤
  deadline.detected      ──┤
  trust.score.updated    ──┼──▶  Aggregation Coordinator
  prediction.generated   ──┤         │
  scheme.status.changed  ──┤         ▼
  identity.verified      ──┘    ┌──────────────┐
                                │ Source Router │
                                └──────┬───────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ Identity     │  │ Metadata     │  │ Eligibility  │
            │ Fetcher      │  │ Fetcher      │  │ Fetcher      │
            └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                   │                 │                  │
                   └─────────────────┼──────────────────┘
                                     ▼
                            ┌──────────────────┐
                            │  Merge Engine     │
                            │                   │
                            │ 1. Validate each  │
                            │    source payload │
                            │ 2. Resolve        │
                            │    conflicts      │
                            │ 3. Compute        │
                            │    derived fields │
                            │ 4. Calculate      │
                            │    completeness   │
                            └────────┬──────────┘
                                     │
                            ┌────────▼──────────┐
                            │  Delta Calculator  │
                            │                    │
                            │ Compare vs last    │
                            │ snapshot, generate │
                            │ JSON Patch ops     │
                            └────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
            ┌──────────────┐ ┌────────────┐ ┌──────────────┐
            │ Profile      │ │ Snapshot   │ │ Event Bus    │
            │ Cache        │ │ Store      │ │ Publisher    │
            │ (Redis)      │ │ (Postgres) │ │              │
            │              │ │            │ │ profile.     │
            │ TTL: 5min    │ │ Partitioned│ │ assembled    │
            └──────────────┘ └────────────┘ └──────────────┘
```

### Assembly Pipeline Steps

| Step | Action | Latency Target |
|---|---|---|
| 1. Trigger | Receive event from Kafka consumer | < 5ms |
| 2. Source Routing | Determine which sources need refresh | < 2ms |
| 3. Parallel Fetch | Fetch all source data concurrently (with circuit breakers) | < 100ms |
| 4. Validation | Validate each source against expected schema | < 10ms |
| 5. Merge | Combine into canonical profile structure | < 15ms |
| 6. Enrichment | Compute derived fields (completeness, risk aggregation) | < 20ms |
| 7. Delta Calculation | Diff against last snapshot | < 15ms |
| 8. Access Masking | Apply consent-based field visibility | < 5ms |
| 9. Serialization | Marshal final JSON + hash | < 10ms |
| 10. Persist + Publish | Write to cache/store + emit event | < 20ms |
| **Total** | | **< 200ms** |

---

## 6. Event Bus Integration

### Consumed Events

| Event | Source | Action |
|---|---|---|
| `user.metadata.updated` | Metadata Engine | Trigger profile reassembly |
| `eligibility.batch.computed` | Eligibility Rules Engine | Update eligibility section |
| `deadline.detected` | Deadline Monitoring Engine | Update deadlines section |
| `trust.score.updated` | Trust Scoring Engine | Update trust section |
| `prediction.generated` | Neural Network Engine | Update predictions section |
| `scheme.application.status_changed` | External/Gov Sync | Update scheme status |
| `identity.verified` | Identity Engine | Update identity section |
| `user.consent.updated` | Identity Engine | Refresh access masking rules |

### Published Events

| Event | Payload | Consumers |
|---|---|---|
| `profile.assembled` | `{ user_id, schema_version, profile_hash, completeness_pct, changed_sections[] }` | Dashboard, Neural Network, Analytics |
| `profile.delta.generated` | `{ user_id, patch_id, base_version, operations[] }` | Dashboard (real-time updates) |
| `profile.completeness.changed` | `{ user_id, old_pct, new_pct, missing_fields[] }` | Dashboard (nudge UI) |
| `profile.snapshot.created` | `{ user_id, snapshot_id, created_at }` | Analytics Warehouse |

---

## 7. NVIDIA Stack Alignment

| NVIDIA Tool | Component | Usage |
|---|---|---|
| **NIM** | Enrichment Pipeline | Invoke Llama 3.1 8B for natural-language summary generation of profile highlights |
| **NeMo BERT** | Completeness Analyzer | Classify missing data importance (critical / optional / nice-to-have) |
| **TensorRT-LLM** | Summary Generation | Optimized inference for profile summary text ("You are eligible for 12 schemes...") |
| **RAPIDS cuDF** | Bulk Export | GPU-accelerated batch profile assembly for analytics export (1M+ profiles) |
| **Triton** | Model Serving | Serve BERT completeness classifier and summary generation models |

### Profile Summary Generation (NIM)

```python
async def generate_profile_summary(profile: dict) -> str:
    """Generate human-readable profile summary using Llama 3.1 8B via NIM."""
    prompt = f"""
    Summarize this citizen's civic profile in 2-3 sentences:
    - Eligible for {profile['eligibility']['total_eligible']} government schemes
    - {len(profile['deadlines']['upcoming'])} upcoming deadlines
    - Profile completeness: {profile['profile_completeness_pct']}%
    - Risk areas: {[k for k, v in profile['risk_scores'].items() if v > 0.15]}
    
    Write in simple, actionable language for an Indian citizen.
    """
    response = await nim_client.generate(
        model="meta/llama-3.1-8b-instruct",
        prompt=prompt,
        max_tokens=150,
        temperature=0.3
    )
    return response.text
```

---

## 8. Scaling Strategy

| Tier | Users | Strategy |
|---|---|---|
| **MVP** | < 10K | Single assembly worker, Redis cache, PostgreSQL snapshots |
| **Growth** | 10K–500K | 3-5 workers with Kafka consumer group partitioning by user region, read replicas |
| **Scale** | 500K–5M | Worker auto-scaling (HPA on queue lag), sharded snapshot store (Citus), edge-cached profiles |
| **Massive** | 5M–50M+ | Regional assembly clusters, pre-computed profile warming, RAPIDS bulk assembly pipeline, tiered caching (L1: local / L2: Redis / L3: CDN) |

### Caching Strategy

```
┌─────────────────────────────────────────────────┐
│              Three-Tier Cache                    │
│                                                  │
│  L1: In-Process (LRU, 1000 profiles, TTL 60s)  │
│         ↓ miss                                   │
│  L2: Redis (all active profiles, TTL 5min)      │
│         ↓ miss                                   │
│  L3: PostgreSQL Snapshot (latest per user)       │
│         ↓ miss                                   │
│  Full Assembly (parallel fetch from sources)     │
│                                                  │
│  Cache Invalidation: Event-driven on source      │
│  update events via Kafka                         │
└─────────────────────────────────────────────────┘
```

---

## 9. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v2/profile/{user_id}` | Get full assembled profile |
| `GET` | `/api/v2/profile/{user_id}?fields=eligibility,deadlines` | Partial profile (sparse fieldset) |
| `GET` | `/api/v2/profile/{user_id}/delta?since={snapshot_id}` | Get delta patch since snapshot |
| `POST` | `/api/v2/profile/{user_id}/assemble` | Force reassembly (admin/trigger) |
| `GET` | `/api/v2/profile/{user_id}/snapshots` | List historical snapshots |
| `GET` | `/api/v2/profile/{user_id}/snapshots/{snapshot_id}` | Get specific snapshot |
| `GET` | `/api/v2/profile/{user_id}/completeness` | Get completeness breakdown |
| `POST` | `/api/v2/profiles/bulk-export` | Batch export (anonymized, admin only) |
| `GET` | `/api/v2/profile/{user_id}/summary` | Get AI-generated profile summary |

### Example Response (Sparse Fieldset)

```json
GET /api/v2/profile/usr_123?fields=eligibility,deadlines

{
  "schema_version": "2.0",
  "profile_id": "prof_abc",
  "generated_at": "2025-01-15T10:30:00Z",
  "eligibility": { ... },
  "deadlines": { ... },
  "_meta": {
    "fields_included": ["eligibility", "deadlines"],
    "cache_hit": true,
    "assembly_latency_ms": 12
  }
}
```

---

## 10. Dependencies

### Upstream (Data Sources)

| Engine | Data Provided |
|---|---|
| Identity Engine | `identity_token`, verified documents, delegation status |
| Processed User Metadata Store | Demographics, economic data, family info |
| Eligibility Rules Engine | Eligible schemes, matched rules, application status |
| Deadline Monitoring Engine | Upcoming/overdue deadlines, alerts |
| Trust Scoring Engine | Confidence scores, source freshness |
| Neural Network Engine | Predictions, recommendations |
| Analytics Warehouse | Cohort tags, aggregated metrics |

### Downstream (Consumers)

| Engine | Data Consumed |
|---|---|
| Dashboard Interface | Full/partial profile for UI rendering |
| Neural Network Engine | Complete context for AI reasoning |
| Simulation Engine | Baseline profile for "what-if" scenarios |
| External API | Consent-gated profile export |
| Analytics Warehouse | Profile snapshots for population analytics |

---

## 11. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ (FastAPI) |
| Framework | FastAPI + asyncio |
| Cache | Redis 7.x (profile cache) |
| Database | PostgreSQL 16 + Citus (snapshot store) |
| Event Bus | Apache Kafka (consumer + producer) |
| Serialization | orjson (fast JSON), msgpack (internal) |
| Schema Validation | Pydantic v2 + JSON Schema |
| Delta Calculation | python-json-patch (RFC 6902) |
| Hashing | SHA-256 (profile integrity) |
| Monitoring | Prometheus + Grafana |
| Tracing | OpenTelemetry |

---

## 12. Implementation Phases

### Phase 1 — Foundation (Weeks 1-2)
- Define canonical profile schema v1 with Pydantic models
- Build aggregation coordinator with parallel source fetching
- Implement Redis profile cache with TTL management
- PostgreSQL snapshot table with monthly partitioning

### Phase 2 — Assembly Pipeline (Weeks 3-4)
- Wire Kafka consumers for all upstream events
- Implement merge engine with conflict resolution
- Build delta calculator (JSON Patch RFC 6902)
- Add profile completeness scoring algorithm

### Phase 3 — Access Control & API (Weeks 5-6)
- Implement consent-aware field masking
- Build REST API endpoints with sparse fieldset support
- Add schema version negotiation
- Build snapshot browsing and historical comparison

### Phase 4 — Intelligence & Scale (Weeks 7-8)
- Integrate NIM for profile summary generation
- NeMo BERT completeness classifier
- Implement three-tier caching strategy
- RAPIDS-powered bulk export pipeline
- Load testing: target < 200ms p99 assembly latency

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Profile assembly latency (p50) | < 100ms |
| Profile assembly latency (p99) | < 200ms |
| Cache hit ratio | > 85% |
| Profile completeness (platform avg) | > 70% |
| Schema validation pass rate | > 99.9% |
| Delta patch size (avg) | < 2KB |
| Snapshot storage per user per month | < 50KB |
| Concurrent profile assemblies | > 5,000/sec |
| Profile freshness (time since source update) | < 30 seconds |
| Zero-downtime schema migrations | 100% |

---

## 14. Design Decisions

### Why a Dedicated Assembly Engine?

| Approach | Pros | Cons |
|---|---|---|
| **Each consumer fetches independently** | Simple | Inconsistent views, N×M queries, coupling |
| **Materialized view in DB** | SQL-native | Rigid schema, poor for nested JSON |
| **Dedicated Assembly Engine (chosen)** | Consistent, cacheable, auditable, consent-aware | Additional service to maintain |

### Conflict Resolution Rules

When multiple sources provide overlapping data:

1. **Identity Engine** is authoritative for identity fields
2. **Eligibility Rules Engine** is authoritative for eligibility verdicts
3. **Most recent timestamp wins** for demographic/economic fields
4. **Trust Scoring Engine** adjudicates when sources disagree on confidence
5. **User-provided data** takes precedence over inferred data (with annotation)

### Privacy-First Assembly

- Fields are **excluded by default** and included only if user consent covers the viewer's access level
- Profile hash enables **tamper detection** without exposing content
- Snapshots support **right-to-erasure** (DPDP Act compliance) via partition-level deletion

---

## 16. Security Hardening

### 16.1 Rate Limiting

<!-- SECURITY: JSON User Info Generator assembles unified profiles from multiple engines.
     Rate limits prevent profile enumeration and excessive cross-service calls.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  # SECURITY: Full profile assembly — triggers calls to 5+ upstream engines
  "/api/v1/profile/assemble":
    per_user:
      requests_per_minute: 10
      burst: 3
    per_ip:
      requests_per_minute: 5

  # SECURITY: Partial profile (specific sections)
  "/api/v1/profile/section/{section}":
    per_user:
      requests_per_minute: 20
      burst: 5

  # SECURITY: Profile snapshot creation
  "/api/v1/profile/snapshot":
    per_user:
      requests_per_hour: 10
      burst: 2

  # SECURITY: Profile diff (compare snapshots)
  "/api/v1/profile/diff":
    per_user:
      requests_per_minute: 10

  # SECURITY: Internal profile assembly (called by other engines)
  internal_endpoints:
    "/internal/profile/assemble":
      per_service:
        requests_per_minute: 200
      allowed_callers: ["eligibility-rules-engine", "simulation-engine", "neural-network-engine"]

  rate_limit_response:
    status: 429
    body:
      error: "rate_limit_exceeded"
      message: "Profile assembly rate limit reached."
```

### 16.2 Input Validation & Sanitization

<!-- SECURITY: Profile assembly involves merging data from multiple engines.
     Validation ensures no injection via upstream data and access control on sections.
     OWASP Reference: API1:2023, API3:2023, API8:2023 -->

```python
# SECURITY: Profile assembly request schema
PROFILE_ASSEMBLY_SCHEMA = {
    "type": "object",
    "required": ["user_id"],
    "additionalProperties": False,
    "properties": {
        "user_id": {
            "type": "string",
            "pattern": "^usr_[a-zA-Z0-9]{12,32}$"
        },
        "sections": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["demographics", "economic", "family", "identity",
                         "eligibility", "documents", "applications", "trust_scores"]
            },
            "maxItems": 8
        },
        "access_level": {
            "type": "string",
            "enum": ["self", "service", "admin"],
            "description": "Determines field-level visibility"
        },
        "include_snapshot": {"type": "boolean", "default": False}
    }
}

# SECURITY: Field-level access control — consent-based visibility
FIELD_ACCESS_MATRIX = {
    "self": ["*"],  # User sees all their own data
    "service": ["demographics.state", "demographics.district", "economic.income_bracket",
                "family.members_count", "identity.age_bracket", "identity.gender",
                "identity.category", "eligibility.*"],  # Services see only necessary fields
    "admin": ["*"],  # Admin with audit trail
}

# SECURITY: Assembled profile sanitization — strip PII for non-self viewers
def sanitize_profile_output(profile: dict, access_level: str) -> dict:
    """Apply field-level access control before returning assembled profile."""
    if access_level == "self":
        return profile  # User sees everything
    allowed = FIELD_ACCESS_MATRIX.get(access_level, [])
    # Filter profile to only allowed fields
    return {k: v for k, v in profile.items() if any(
        k.startswith(a.replace('.*', '')) for a in allowed
    )}

# SECURITY: Profile hash for tamper detection
import hashlib
def compute_profile_hash(profile: dict) -> str:
    """SHA-256 hash of profile for integrity verification."""
    import json
    canonical = json.dumps(profile, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
```

### 16.3 Secure API Key & Secret Management

```yaml
secrets_management:
  environment_variables:
    - DB_PASSWORD               # PostgreSQL (profile snapshots)
    - REDIS_PASSWORD            # Assembly cache
    - KAFKA_SASL_PASSWORD       # Event bus auth
    - IDENTITY_SERVICE_TOKEN    # Identity Engine access
    - METADATA_SERVICE_TOKEN    # Metadata Engine access
    - ELIGIBILITY_SERVICE_TOKEN # Eligibility Rules Engine access
    - ENCRYPTION_KEY            # Profile-level encryption key

  rotation_policy:
    db_credentials: 90_days
    service_tokens: 90_days
    encryption_key: 365_days  # Longer rotation with key versioning

  # SECURITY: Profile data is PII-heavy — encryption mandatory
  encryption:
    profiles_encrypted_at_rest: true
    snapshots_encrypted: true
    algorithm: AES-256-GCM
    key_source: KMS
```

### 16.4 OWASP Compliance

| OWASP Risk | Mitigation |
|---|---|
| **API1: BOLA** | Users can only assemble their own profile; service tokens scoped per engine |
| **API2: Broken Auth** | JWT validation; service-to-service tokens for internal endpoints |
| **API3: Broken Property Auth** | Field-level access matrix; consent-based visibility |
| **API4: Resource Consumption** | Assembly rate limited; snapshot creation capped per hour |
| **API5: Broken Function Auth** | Snapshot deletion requires admin; profile assembly scoped by JWT |
| **API6: Sensitive Flows** | Profile hash for tamper detection; snapshots support right-to-erasure |
| **API7: SSRF** | No URL inputs; all data from internal service calls only |
| **API8: Misconfig** | Service tokens have minimal scope; admin access logged |
| **API9: Improper Inventory** | Profile schema versioned; deprecated sections flagged |
| **API10: Unsafe Consumption** | Upstream engine responses validated against expected schema |

---

## ⚙️ Build Phase Instructions (Current Phase Override)

> **These instructions override any conflicting guidance above for the current local build phase.**

### 1. Local-First Architecture
- Build and run this engine **entirely locally**. Do NOT integrate any AWS cloud services (KMS, etc.).
- Use local encryption (Python `cryptography` library) instead of cloud KMS.
- Store all secrets in a local `.env` file.

### 2. Data Storage & Caching (Zero-Redundancy)
- Before assembling or fetching any user profile data, **always check if the target data already exists locally**.
- If present locally → skip re-assembly and load directly from the local cache.
- Only re-assemble if profile data has **changed** (use JSON Patch delta detection).
- Cache assembled profiles locally in Redis (local) with appropriate TTL.

### 3. Deferred Features (Do NOT Implement Yet)
- **Notifications & Messaging**: Do not build or integrate any notification systems.
- **Cloud KMS**: Use local encryption libraries instead.

### 4. Primary Focus
Build a robust, locally-functioning JSON user info generator with:
- Unified profile assembly from internal engine outputs
- JSON Patch delta computation (RFC 6902)
- Profile snapshot management
- Field-level access control
- All functionality testable without any cloud dependencies
