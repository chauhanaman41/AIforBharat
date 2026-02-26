# 🟦 Metadata Engine — Design & Plan

## 1. Purpose

The Metadata Engine transforms **raw user input into structured, normalized user profiles**. It is the bridge between unstructured user data and the structured metadata needed by AI engines, eligibility rules, and analytics systems.

Every piece of information a user provides — age, income, state, marital status, employment, dependents, business category — is validated, normalized, and versioned into a **canonical metadata JSON** that the rest of the platform can reliably consume.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Input Normalization** | Convert free-text/voice input into structured fields |
| **Schema Validation** | Validate every metadata field against versioned schemas |
| **Profile Enrichment** | Derive secondary attributes from primary inputs |
| **Versioned Models** | Track metadata schema evolution over time |
| **Multi-Source Fusion** | Merge data from registration, voice, forms, DigiLocker |
| **Derived Attributes** | Compute age group, income bracket, life stage |
| **Conflict Resolution** | Handle contradictory inputs from multiple sources |
| **Temporal Metadata** | Track how user metadata changes over time |
| **Batch Processing** | Bulk metadata normalization for migrations |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Input Sources                              │
│                                                              │
│  Registration │ Voice Input │ Form Update │ DigiLocker │ API │
└────────────────────────────┬─────────────────────────────────┘
                             │ Events / API calls
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    Metadata Engine                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Input Parser                             │    │
│  │                                                      │    │
│  │  • Free-text → Structured    (NLP extraction)        │    │
│  │  • Voice → Text → Structured (via Riva pipeline)     │    │
│  │  • Form → Direct mapping                             │    │
│  │  • API → Schema validation                           │    │
│  └──────────────────────────┬───────────────────────────┘    │
│                             │                                │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │              Schema Validator                         │    │
│  │                                                      │    │
│  │  • JSON Schema validation                            │    │
│  │  • Type coercion (string "25" → int 25)              │    │
│  │  • Range validation (age: 0-150, income: >= 0)       │    │
│  │  • Enum validation (state codes, categories)         │    │
│  │  • Required field checks                             │    │
│  └──────────────────────────┬───────────────────────────┘    │
│                             │                                │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │              Derivation Engine                        │    │
│  │                                                      │    │
│  │  • age → age_group (child/youth/adult/senior)        │    │
│  │  • income → income_bracket (BPL/LIG/MIG/HIG)        │    │
│  │  • age + marital_status → life_stage                 │    │
│  │  • occupation + income → employment_category         │    │
│  │  • state + district → region_code                    │    │
│  └──────────────────────────┬───────────────────────────┘    │
│                             │                                │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │              Conflict Resolver                        │    │
│  │                                                      │    │
│  │  • Source priority: DigiLocker > Form > Voice > API  │    │
│  │  • Timestamp-based: Latest wins (configurable)       │    │
│  │  • Flag conflicts for manual review                  │    │
│  └──────────────────────────┬───────────────────────────┘    │
│                             │                                │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │              Version Manager                          │    │
│  │                                                      │    │
│  │  • Schema version tracking                           │    │
│  │  • Migration between schema versions                 │    │
│  │  • Backward compatibility enforcement                │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────┬───────────────────────────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
┌──────────────────┐ ┌────────────────┐ ┌──────────────┐
│ Processed User   │ │ Event Bus      │ │ Raw Data     │
│ Metadata Store   │ │ (Publish       │ │ Store        │
│ (PostgreSQL)     │ │  metadata      │ │ (Audit)      │
│                  │ │  events)       │ │              │
└──────────────────┘ └────────────────┘ └──────────────┘
```

### 3.2 Stateless Processing

- Each metadata transformation is a **pure function** — no side effects
- Engine maintains **no internal state** — all state in PostgreSQL
- Horizontally scalable — add more workers for throughput
- Idempotent operations — same input always produces same output

---

## 4. Data Models

### 4.1 Normalized User Metadata (Output)

```json
{
  "metadata_id": "meta_uuid_v4",
  "user_id": "usr_uuid_v4",
  "identity_token": "idt_a1b2c3d4",
  "schema_version": "2.1.0",
  "timestamp": "2026-02-26T10:05:00Z",
  
  "primary_attributes": {
    "age": 34,
    "date_of_birth": "1992-05-15",
    "gender": "male",
    "marital_status": "married",
    "state": "UP",
    "district": "Lucknow",
    "pincode": "226001",
    "residence_type": "urban"
  },
  
  "economic_attributes": {
    "annual_income": 450000,
    "income_source": "salaried",
    "employer_type": "private",
    "has_bank_account": true,
    "has_jan_dhan": false,
    "land_holding_acres": 0,
    "ration_card_type": "APL"
  },
  
  "family_attributes": {
    "dependents_count": 2,
    "children_count": 1,
    "children_ages": [5],
    "elderly_dependents": 1,
    "family_size": 4
  },
  
  "derived_attributes": {
    "age_group": "adult",
    "income_bracket": "LIG",
    "life_stage": "young_family",
    "employment_category": "formal_private",
    "region_code": "UP_LKO",
    "bpl_status": false,
    "tax_bracket": "5%",
    "social_category": "general"
  },
  
  "source_tracking": {
    "primary_source": "registration_form",
    "last_updated_by": "user_profile_update",
    "confidence_scores": {
      "income": 0.85,
      "age": 1.0,
      "state": 1.0,
      "marital_status": 0.95
    }
  }
}
```

### 4.2 Schema Version Registry

```json
{
  "schema_id": "user_metadata",
  "versions": [
    {
      "version": "1.0.0",
      "released": "2026-01-01",
      "status": "deprecated",
      "fields_count": 15
    },
    {
      "version": "2.0.0",
      "released": "2026-02-01",
      "status": "active",
      "fields_count": 28,
      "breaking_changes": ["income renamed to annual_income"]
    },
    {
      "version": "2.1.0",
      "released": "2026-02-20",
      "status": "active",
      "fields_count": 32,
      "additions": ["social_category", "tax_bracket", "bpl_status", "ration_card_type"]
    }
  ]
}
```

---

## 5. Context Flow

```
Input received (event or API call)
    │
    ├─► Input Parser
    │       │
    │       ├─► Identify input format (form / voice / API / document)
    │       ├─► Extract structured fields
    │       └─► Normalize values (trim, lowercase, standardize)
    │
    ├─► Schema Validator
    │       │
    │       ├─► Load target schema version
    │       ├─► Validate types, ranges, enums
    │       ├─► Coerce compatible types
    │       └─► Reject invalid fields with descriptive errors
    │
    ├─► Derivation Engine
    │       │
    │       ├─► Compute derived attributes from primary attributes
    │       ├─► Apply business rules (income brackets, life stages)
    │       └─► Calculate confidence scores
    │
    ├─► Conflict Resolver (if updating existing profile)
    │       │
    │       ├─► Compare with existing metadata
    │       ├─► Apply source priority rules
    │       ├─► Flag unresolvable conflicts
    │       └─► Merge resolved metadata
    │
    ├─► Version Manager
    │       │
    │       ├─► Stamp with current schema version
    │       ├─► Migrate if input was in older schema
    │       └─► Validate final output against schema
    │
    └─► Output
            │
            ├─► Write to Processed User Metadata Store
            ├─► Publish METADATA_UPDATED event to Event Bus
            └─► Log transformation to Raw Data Store
```

---

## 6. Event Bus Integration

| Event Consumed | Source | Action |
|---|---|---|
| `USER_REGISTERED` | Login Engine | Create initial metadata from registration data |
| `PROFILE_UPDATED` | Dashboard | Update metadata with new user input |
| `DOCUMENT_VERIFIED` | Identity Engine | Enrich metadata with verified data |
| `VOICE_INPUT_PROCESSED` | Speech Engine | Extract metadata from voice conversation |

| Event Published | Consumers |
|---|---|
| `METADATA_CREATED` | Eligibility Rules Engine, JSON User Info Generator |
| `METADATA_UPDATED` | Eligibility Rules Engine, AI Core, JSON User Info Generator |
| `METADATA_CONFLICT` | Dashboard (for user resolution), Admin |
| `SCHEMA_MIGRATED` | Analytics Warehouse |

---

## 7. NVIDIA Stack Alignment

| Component | NVIDIA Tool | Usage |
|---|---|---|
| NLP extraction from text | NeMo BERT | Extract structured fields from free-text input |
| Voice → metadata pipeline | NVIDIA Riva + NeMo | Speech-to-text → NLP extraction |
| Batch normalization | RAPIDS cuDF | GPU-accelerated bulk metadata processing |
| Schema validation at scale | — | Standard CPU (not GPU-dependent) |

---

## 8. Scaling Strategy

| Scale Tier | Users | Strategy |
|---|---|---|
| **Tier 1** (MVP) | < 10K | Single service instance, direct DB writes |
| **Tier 2** | 10K – 1M | Kafka consumers, async processing, batch optimization |
| **Tier 3** | 1M – 10M | Worker pool with auto-scaling, schema cache in Redis |
| **Tier 4** | 10M+ | GPU-accelerated batch processing, regional workers |

### Key Decisions

- **Stateless workers**: No local state; all state in PostgreSQL
- **Schema cache**: Redis cache for schema definitions (avoid DB reads on every validation)
- **Batch processing**: Aggregate low-priority updates into micro-batches
- **Idempotency**: Every transformation keyed on `(user_id, input_hash)` to prevent duplicates

---

## 9. API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/metadata/process` | Process raw input into normalized metadata |
| `GET` | `/api/v1/metadata/user/{user_id}` | Get user's current metadata |
| `GET` | `/api/v1/metadata/user/{user_id}/history` | Get metadata version history |
| `GET` | `/api/v1/metadata/schemas` | List all schema versions |
| `GET` | `/api/v1/metadata/schemas/{version}` | Get specific schema definition |
| `POST` | `/api/v1/metadata/batch` | Batch process multiple users |
| `POST` | `/api/v1/metadata/validate` | Validate input without persisting |

---

## 10. Dependencies

| Dependency | Direction | Purpose |
|---|---|---|
| **Login/Register Engine** | Upstream | Initial user data from registration |
| **Identity Engine** | Upstream | Verified identity data enrichment |
| **Speech Interface Engine** | Upstream | Voice-extracted metadata |
| **Processed User Metadata Store** | Downstream | Persists normalized metadata |
| **Eligibility Rules Engine** | Downstream | Consumes metadata for eligibility checks |
| **JSON User Info Generator** | Downstream | Uses metadata to build complete profiles |
| **Event Bus** | Bidirectional | Consumes input events, publishes metadata events |
| **Raw Data Store** | Downstream | Audit logging |

---

## 11. Technology Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11 (FastAPI) |
| Schema Validation | JSON Schema (Draft 2020-12) / Pydantic v2 |
| NLP Extraction | NVIDIA NeMo BERT / spaCy |
| Processing | Async workers (Celery / ARQ) |
| Schema Registry | Custom + Redis cache |
| Event Bus | Apache Kafka / NATS |
| Testing | pytest + hypothesis (property-based testing) |
| Containerization | Docker + Kubernetes |

---

## 12. Implementation Phases

| Phase | Milestone | Timeline |
|---|---|---|
| **Phase 1** | Basic schema validation, form input processing | Week 1-2 |
| **Phase 2** | Derived attribute computation, income/age brackets | Week 3-4 |
| **Phase 3** | Multi-source conflict resolution | Week 5 |
| **Phase 4** | Schema versioning and migration system | Week 6-7 |
| **Phase 5** | NLP extraction from free-text and voice input | Week 8-10 |
| **Phase 6** | Batch processing, GPU-accelerated normalization | Week 12-14 |

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Metadata processing latency (P95) | < 100ms |
| Schema validation accuracy | 100% |
| Derived attribute accuracy | > 97% |
| NLP extraction accuracy | > 90% |
| Conflict resolution automation rate | > 80% |
| Schema migration success rate | > 99.9% |

---

## 14. Official Data Sources — Demographics & Metadata (MVP)

| Data Required | Official Source | URL | Notes |
|---|---|---|---|
| Census population data, demographic breakdown | Census India | https://censusindia.gov.in | State/district-level demographic reference |
| Aadhaar stats (public aggregated) | UIDAI Stats Portal | https://uidai.gov.in | Aggregated statistics only — not identity data |
| Socio-economic datasets, structured indicators | National Data & Analytics Platform (NDAP) | https://ndap.niti.gov.in | Curated datasets from NITI Aayog |
| Development indicators, policy indices | NITI Aayog | https://www.niti.gov.in | District-level development metrics |

### Usage in Metadata Engine

- **Census India** → Validate demographic field ranges (state populations, district codes, rural/urban classification)
- **UIDAI Stats** → Cross-reference Aadhaar saturation for KYC coverage estimates
- **NDAP** → Derive income brackets, BPL thresholds by region
- **NITI Aayog** → Index-based derivations (HDI, SDG indicators per district)
