# Government Data Sync Engine — Design & Plan

## 1. Purpose

The Government Data Sync Engine is the **continuous synchronization bridge** between the AIforBharat platform and official government data sources. It tracks amendments to existing schemes, detects repealed or sunset policies, monitors budget reallocations, ingests gazette notifications, and ensures the platform's rule base remains current and legally accurate.

Unlike the Policy Fetching Engine (which crawls and discovers new policies), this engine focuses on **change management** — detecting modifications to already-tracked policies and propagating those changes through the platform's rule and knowledge layers. It is the authoritative source of truth for "what changed, when, and how it affects users."

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Amendment Tracking** | Detect changes to scheme eligibility criteria, benefit amounts, deadlines |
| **Repeal Detection** | Identify when schemes are discontinued, sunset, or merged |
| **Budget Reallocation Monitoring** | Track fund allocation changes that affect scheme availability |
| **Gazette Notification Ingestion** | Parse official gazette entries for policy changes |
| **Circular/Office Memorandum Tracking** | Monitor departmental circulars that modify scheme implementation |
| **Version Diffing** | Compute structured diffs between policy versions |
| **Impact Assessment** | Estimate number of users affected by each change |
| **Change Propagation** | Trigger downstream rule updates, eligibility re-evaluation, and user notifications |
| **Regulatory Calendar** | Track legislative sessions, budget announcements, election code periods |
| **Data Quality Monitoring** | Validate government data source availability and freshness |

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                 Government Data Sync Engine                    │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                Change Detection Layer                      │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │ │
│  │  │ Gazette    │  │ Portal     │  │ API              │    │ │
│  │  │ Monitor    │  │ Change     │  │ Polling          │    │ │
│  │  │            │  │ Detector   │  │                  │    │ │
│  │  │ eGazette   │  │ Content    │  │ data.gov.in      │    │ │
│  │  │ parser     │  │ hash diff  │  │ scheme APIs      │    │ │
│  │  └────────────┘  └────────────┘  └──────────────────┘    │ │
│  └──────────────────────────┬───────────────────────────────┘ │
│                             │                                  │
│  ┌──────────────────────────▼───────────────────────────────┐ │
│  │                Change Processing Layer                     │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │ │
│  │  │ Diff       │  │ Amendment  │  │ Impact           │    │ │
│  │  │ Engine     │  │ Classifier │  │ Estimator        │    │ │
│  │  │            │  │            │  │                  │    │ │
│  │  │ Structured │  │ NeMo BERT: │  │ Count affected   │    │ │
│  │  │ diff: old  │  │ major/minor│  │ users per        │    │ │
│  │  │ vs new     │  │ /cosmetic  │  │ change           │    │ │
│  │  └────────────┘  └────────────┘  └──────────────────┘    │ │
│  └──────────────────────────┬───────────────────────────────┘ │
│                             │                                  │
│  ┌──────────────────────────▼───────────────────────────────┐ │
│  │                Propagation Layer                           │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │ │
│  │  │ Rule       │  │ Vector     │  │ Notification     │    │ │
│  │  │ Updater    │  │ Re-indexer │  │ Generator        │    │ │
│  │  │            │  │            │  │                  │    │ │
│  │  │ Update     │  │ Re-embed   │  │ Notify affected  │    │ │
│  │  │ eligibility│  │ changed    │  │ users about      │    │ │
│  │  │ rules      │  │ policies   │  │ changes          │    │ │
│  │  └────────────┘  └────────────┘  └──────────────────┘    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                Version Store                               │ │
│  │                                                            │ │
│  │  Policy versions, amendment history, gazette archive       │ │
│  │  PostgreSQL + S3 (original documents)                     │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Data Models

### 4.1 Policy Amendment Record

```json
{
  "amendment_id": "amd_uuid_v4",
  "scheme_id": "sch_pm_kisan",
  "scheme_name": "PM-KISAN",
  
  "amendment_type": "eligibility_change",
  "classification": "major",
  "source_type": "gazette_notification",
  "source_url": "https://egazette.gov.in/...",
  "source_document_id": "doc_uuid",
  
  "detected_at": "2025-01-15T08:00:00Z",
  "effective_date": "2025-04-01",
  "gazette_date": "2025-01-10",
  
  "changes": [
    {
      "field": "eligibility.income_cap",
      "old_value": 200000,
      "new_value": 250000,
      "change_type": "relaxed",
      "description": "Income eligibility cap increased from ₹2L to ₹2.5L"
    },
    {
      "field": "benefit.amount",
      "old_value": 6000,
      "new_value": 8000,
      "change_type": "increased",
      "description": "Annual benefit increased from ₹6,000 to ₹8,000"
    }
  ],
  
  "impact_estimate": {
    "users_newly_eligible": 125000,
    "users_benefit_increased": 450000,
    "users_lost_eligibility": 0,
    "budget_impact_crore": 850
  },
  
  "propagation_status": {
    "rules_updated": true,
    "vectors_re_indexed": true,
    "users_notified": false,
    "notifications_pending": 575000
  },
  
  "verification": {
    "auto_verified": false,
    "manual_review_required": true,
    "reviewer": null,
    "verified_at": null
  }
}
```

### 4.2 Policy Version Table

```sql
CREATE TABLE policy_versions (
    version_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheme_id         VARCHAR(64) NOT NULL,
    version_number    INTEGER NOT NULL,
    
    -- Content
    policy_text       TEXT NOT NULL,
    policy_hash       VARCHAR(64) NOT NULL,
    structured_data   JSONB NOT NULL,
    
    -- Source
    source_type       VARCHAR(32) NOT NULL,  -- gazette, portal, api, manual
    source_url        TEXT,
    source_document   VARCHAR(64),  -- S3 key for original document
    
    -- Dates
    published_date    DATE,
    effective_date    DATE NOT NULL,
    sunset_date       DATE,  -- null if no expiry
    detected_at       TIMESTAMPTZ DEFAULT NOW(),
    
    -- Status
    status            VARCHAR(20) DEFAULT 'active',
    -- active, superseded, repealed, sunset, draft
    
    superseded_by     UUID,  -- Points to next version
    
    UNIQUE (scheme_id, version_number)
);

CREATE TABLE amendments (
    amendment_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheme_id         VARCHAR(64) NOT NULL,
    old_version_id    UUID NOT NULL REFERENCES policy_versions(version_id),
    new_version_id    UUID NOT NULL REFERENCES policy_versions(version_id),
    
    amendment_type    VARCHAR(32) NOT NULL,
    classification    VARCHAR(16) NOT NULL, -- major, minor, cosmetic
    
    changes           JSONB NOT NULL,
    impact_estimate   JSONB,
    
    source_type       VARCHAR(32) NOT NULL,
    gazette_number    VARCHAR(64),
    gazette_date      DATE,
    effective_date    DATE NOT NULL,
    
    -- Processing
    auto_detected     BOOLEAN DEFAULT true,
    verified          BOOLEAN DEFAULT false,
    verified_by       VARCHAR(64),
    verified_at       TIMESTAMPTZ,
    
    -- Propagation
    rules_updated     BOOLEAN DEFAULT false,
    vectors_updated   BOOLEAN DEFAULT false,
    users_notified    BOOLEAN DEFAULT false,
    
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_amendments_scheme ON amendments (scheme_id, effective_date DESC);
CREATE INDEX idx_amendments_unverified ON amendments (verified) WHERE verified = false;
```

### 4.3 Government Source Registry

```json
{
  "source_id": "src_egazette",
  "name": "eGazette of India",
  "type": "gazette",
  "base_url": "https://egazette.gov.in",
  "polling_interval_hours": 6,
  "last_polled_at": "2025-01-15T06:00:00Z",
  "last_change_detected": "2025-01-10T12:00:00Z",
  "health_status": "healthy",
  "availability_30d_pct": 98.5,
  "parser_type": "gazette_pdf_parser",
  "priority": "critical",
  "coverage": {
    "central_schemes": true,
    "state_schemes": false,
    "legislative_acts": true,
    "ordinances": true
  }
}
```

---

## 5. Context Flow

```
Government Sources:
  ┌─────────────────────────────────────────────────┐
  │ eGazette ─── Portal Changes ─── data.gov.in    │
  │ Budget Docs ── Circulars ─── RTI Responses      │
  │ Legislative Assembly ─── Press Releases          │
  └────────────────────────┬────────────────────────┘
                           │
  ┌────────────────────────▼────────────────────────┐
  │          Change Detection                        │
  │                                                  │
  │  For each registered source:                     │
  │  1. Fetch latest content                         │
  │  2. Compute content hash                         │
  │  3. Compare with stored hash                     │
  │  4. If changed → extract diff                    │
  │  5. If new gazette → parse and classify          │
  └────────────────────────┬────────────────────────┘
                           │
  ┌────────────────────────▼────────────────────────┐
  │          Change Classification (NeMo BERT)       │
  │                                                  │
  │  Classify amendment:                             │
  │  - major: eligibility/benefit/deadline change    │
  │  - minor: procedural/documentation change        │
  │  - cosmetic: language/formatting only            │
  │                                                  │
  │  Classify type:                                  │
  │  - eligibility_change                            │
  │  - benefit_change                                │
  │  - deadline_change                               │
  │  - scheme_repeal                                 │
  │  - scheme_merge                                  │
  │  - budget_reallocation                           │
  └────────────────────────┬────────────────────────┘
                           │
  ┌────────────────────────▼────────────────────────┐
  │          Impact Analysis                         │
  │                                                  │
  │  Estimate affected user count by querying:       │
  │  - Processed User Metadata Store (demographics)  │
  │  - Current eligibility cache (who matches today) │
  │  - Simulate new rules against user base          │
  └────────────────────────┬────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
  │ Rule Updater │ │ Vector       │ │ Notification │
  │              │ │ Re-indexer   │ │ Publisher    │
  │ Update YAML  │ │              │ │              │
  │ rules in     │ │ Re-embed     │ │ Publish      │
  │ Eligibility  │ │ updated      │ │ policy.      │
  │ Rules Engine │ │ policy in    │ │ changed      │
  │              │ │ Milvus       │ │ events       │
  └──────────────┘ └──────────────┘ └──────────────┘
```

---

## 6. Event Bus Integration

### Consumed Events

| Event | Source | Action |
|---|---|---|
| `policy.document.fetched` | Policy Fetching Engine | Check for changes against existing versions |
| `policy.new.discovered` | Policy Fetching Engine | Ingest as new policy version |
| `gazette.published` | eGazette Monitor | Parse for scheme amendments |
| `budget.announced` | Budget Monitor | Track allocation changes |

### Published Events

| Event | Payload | Consumers |
|---|---|---|
| `policy.amended` | `{ scheme_id, amendment_type, changes[], effective_date }` | Eligibility Rules Engine, Chunks Engine |
| `policy.repealed` | `{ scheme_id, repeal_date, replacement_scheme_id }` | All downstream engines |
| `policy.rules.updated` | `{ scheme_id, rule_version, changed_fields[] }` | Eligibility Rules Engine |
| `policy.vectors.stale` | `{ scheme_id, version_id }` | Vector Database, Chunks Engine |
| `policy.deadline.amended` | `{ scheme_id, old_deadline, new_deadline }` | Deadline Monitoring Engine |
| `budget.reallocated` | `{ scheme_id, old_allocation, new_allocation, fiscal_year }` | Analytics Warehouse |
| `policy.impact.estimated` | `{ amendment_id, affected_users_count }` | Dashboard, Analytics |

---

## 7. NVIDIA Stack Alignment

| NVIDIA Tool | Component | Usage |
|---|---|---|
| **NeMo BERT** | Amendment Classifier | Classify changes as major/minor/cosmetic |
| **NeMo BERT** | Change Type Detection | Categorize: eligibility/benefit/deadline/repeal |
| **NIM** | Diff Summarization | Llama 3.1 8B summarizes policy diffs in plain language |
| **NeMo NER** | Entity Extraction | Extract dates, amounts, thresholds from gazette text |
| **TensorRT-LLM** | Batch Processing | Optimized inference for processing gazette backlog |
| **Triton** | Model Serving | Serve BERT classifier and NER models |

### Amendment Classification

```python
async def classify_amendment(
    old_text: str,
    new_text: str,
    diff_summary: str
) -> dict:
    """Classify amendment severity and type using NeMo BERT."""
    
    # Classification head: major / minor / cosmetic
    severity = await nemo_classifier.predict(
        model="amendment-severity-classifier",
        text=diff_summary,
        labels=["major", "minor", "cosmetic"]
    )
    
    # Multi-label classification: what changed?
    change_types = await nemo_classifier.predict(
        model="amendment-type-classifier",
        text=diff_summary,
        labels=[
            "eligibility_change", "benefit_change",
            "deadline_change", "scheme_repeal",
            "scheme_merge", "budget_reallocation",
            "procedural_change", "documentation_change"
        ],
        multi_label=True
    )
    
    return {
        "classification": severity.label,
        "confidence": severity.score,
        "change_types": [ct.label for ct in change_types if ct.score > 0.5]
    }
```

---

## 8. Scaling Strategy

| Tier | Users | Strategy |
|---|---|---|
| **MVP** | < 10K | Manual gazette uploads + automated central portal monitoring, 50 sources |
| **Growth** | 10K–500K | 200+ sources, automated gazette parsing, NLP classification, 6-hour polling |
| **Scale** | 500K–5M | 500+ sources, real-time gazette alerts, auto-rule-update pipeline, impact estimation |
| **Massive** | 5M–50M+ | 1000+ sources (all states + UTs), ML-powered change detection, auto-propagation with human-in-the-loop for major changes |

### Change Propagation SLA

| Amendment Class | Detection → Rule Update | Detection → User Notification |
|---|---|---|
| **Major** (eligibility change) | < 4 hours (+ manual review) | < 24 hours |
| **Minor** (procedural) | < 24 hours (auto) | < 72 hours |
| **Cosmetic** | < 7 days (auto) | No notification |
| **Repeal** | < 2 hours (manual + auto) | < 12 hours |

---

## 9. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/sync/amendments` | List recent amendments |
| `GET` | `/api/v1/sync/amendments/{scheme_id}` | Amendment history for scheme |
| `GET` | `/api/v1/sync/versions/{scheme_id}` | Version history for scheme |
| `GET` | `/api/v1/sync/versions/{scheme_id}/{version}` | Specific policy version |
| `GET` | `/api/v1/sync/diff/{scheme_id}/{v1}/{v2}` | Diff between two versions |
| `GET` | `/api/v1/sync/sources` | List monitored sources + health |
| `POST` | `/api/v1/sync/sources/{source_id}/poll` | Force-poll a source |
| `GET` | `/api/v1/sync/pending-review` | Amendments awaiting manual review |
| `POST` | `/api/v1/sync/amendments/{id}/verify` | Verify/approve amendment (admin) |
| `GET` | `/api/v1/sync/calendar` | Regulatory calendar (budget sessions, etc.) |

---

## 10. Dependencies

### Upstream

| Engine | Data Provided |
|---|---|
| Policy Fetching Engine | Raw documents, crawled policy text |
| Document Understanding Engine | Structured extraction from gazette PDFs |

### Downstream

| Engine | Data Consumed |
|---|---|
| Eligibility Rules Engine | Updated rule definitions |
| Chunks Engine | Re-chunking of amended policies |
| Vector Database | Re-embedding of changed content |
| Deadline Monitoring Engine | Amended deadline dates |
| Analytics Warehouse | Budget reallocation data |
| Dashboard Interface | Change notifications for affected users |
| Neural Network Engine | Updated context for AI reasoning |

---

## 11. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| Scheduler | Celery Beat + Redis (polling schedules) |
| Database | PostgreSQL 16 (version store, amendments) |
| Object Store | S3/MinIO (original gazette documents) |
| Diff Engine | difflib (text) + custom JSON diff |
| NLP | NVIDIA NeMo BERT (classification, NER) |
| LLM | NVIDIA NIM (Llama 3.1 8B for summarization) |
| Event Bus | Apache Kafka |
| PDF Parser | PyMuPDF + pdfplumber |
| Monitoring | Prometheus + Grafana |

---

## 12. Implementation Phases

### Phase 1 — Foundation (Weeks 1-2)
- Government source registry with health monitoring
- Content hash-based change detection for top 50 portals
- PostgreSQL version store with structured diff
- Basic amendment record creation

### Phase 2 — Classification & Propagation (Weeks 3-4)
- NeMo BERT amendment classifier (major/minor/cosmetic)
- Change type detection (eligibility/benefit/deadline/repeal)
- Event publishing for downstream engines
- Rule update propagation to Eligibility Rules Engine

### Phase 3 — Gazette Processing (Weeks 5-6)
- eGazette PDF parser pipeline
- NER for date/amount/threshold extraction
- Impact estimation (affected user count)
- Admin review UI for major amendments
- Manual verification workflow

### Phase 4 — Scale & Automation (Weeks 7-8)
- 200+ source monitoring with regional coverage
- Auto-rule-update pipeline for minor/cosmetic changes
- Regulatory calendar with legislative session tracking
- Budget reallocation monitoring
- SLA monitoring: detection-to-propagation time

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Amendment detection accuracy | > 95% |
| Detection latency (gazette → detection) | < 6 hours |
| Classification accuracy (major/minor/cosmetic) | > 90% |
| Auto-propagation success rate (minor changes) | > 95% |
| Manual review turnaround (major changes) | < 24 hours |
| Source monitoring uptime | > 99% |
| False positive rate (non-changes detected as changes) | < 5% |
| Policy version currency (% of schemes on latest version) | > 95% |
| Downstream propagation completeness | 100% |
| Government source coverage (central + state) | > 80% |

---

## 14. Official Data Sources (MVP)

| Data Required | Official Source | URL | Notes |
|---|---|---|---|
| Gazette notifications, amendments | eGazette | https://egazette.nic.in | Primary source for legal policy changes |
| Policy announcements, daily updates | Press Information Bureau (PIB) | https://pib.gov.in | Daily official press releases |
| Acts, amendments, legal texts | India Code | https://www.indiacode.nic.in | Full text for diff computation |
| Scheme datasets, metadata changes | Open Government Data Portal | https://data.gov.in | Structured scheme data with API access |
| Govt programs overview | MyGov | https://www.mygov.in | Policy summaries and program updates |
| Budget reallocation data | Union Budget Portal | https://www.indiabudget.gov.in | Annual budget allocation PDFs |

### Optional Future — Global Comparative Policy

| Data | Source | URL | Notes |
|---|---|---|---|
| Global economic indicators | World Bank | https://data.worldbank.org | Open data for cross-country comparison |
| IMF datasets | IMF Data | https://data.imf.org | Free macroeconomic and fiscal data |
| UN development data | UN Data | https://data.un.org | SDG, HDI, population data |

### Change Detection Priority

| Priority | Source | Monitoring Frequency |
|---|---|---|
| **P0 — Critical** | eGazette | Every 2 hours |
| **P0 — Critical** | India Code | Every 6 hours |
| **P1 — High** | PIB | Every 4 hours |
| **P1 — High** | data.gov.in | Every 6 hours |
| **P2 — Medium** | Union Budget Portal | Daily (budget season: hourly) |
| **P3 — Low** | MyGov | Daily |
