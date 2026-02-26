# 🔍 Policy Fetching Engine — Design & Plan

## 1. Purpose

The Policy Fetching Engine is the **data acquisition layer** that scrapes, monitors, and ingests government policy data from official portals, Gazette of India, budget documents, ministry websites, and state government portals. It ensures the platform always has the **latest, most accurate policy data**.

**Core Mission:** Continuously monitor 100+ government data sources and deliver structured policy data within minutes of publication — ensuring no citizen misses a benefit due to stale information.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Official Portal Scraping** | Scrape policy data from government websites |
| **Gazette Monitoring** | Monitor Gazette of India for new notifications |
| **Budget Update Tracking** | Fetch Union and State budget announcements |
| **Amendment Tracking** | Detect policy amendments and rule changes |
| **Change Detection** | Identify what changed vs. previous version |
| **Delta Storage** | Store only the differences between versions |
| **Scheduled Crawlers** | Configurable crawl schedules per source |
| **Webhook Integration** | Receive push notifications from data.gov.in APIs |
| **Multi-Format Support** | PDF, HTML, JSON, XML, Excel parsing |
| **Source Health Monitoring** | Track source availability and freshness |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Government Data Sources                    │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ PMIndia  │ │ Gazette  │ │ Data.gov │ │ State        │   │
│  │ .gov.in  │ │ of India │ │ .in APIs │ │ Portals (36) │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ Ministry │ │ RBI      │ │ Budget   │                    │
│  │ Websites │ │ Portal   │ │ Documents│                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP / API / RSS
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                  Policy Fetching Engine                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Crawler Manager                          │    │
│  │                                                      │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │    │
│  │  │ Scheduled  │  │ Event-     │  │ Webhook        │  │    │
│  │  │ Crawler    │  │ Triggered  │  │ Receiver       │  │    │
│  │  │ (Cron)     │  │ Crawler    │  │                │  │    │
│  │  └────────────┘  └────────────┘  └────────────────┘  │    │
│  └──────────────────────────┬───────────────────────────┘    │
│                             │                                │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │              Fetch & Parse Layer                       │    │
│  │                                                      │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │    │
│  │  │ HTTP       │  │ PDF        │  │ HTML           │  │    │
│  │  │ Fetcher    │  │ Extractor  │  │ Scraper        │  │    │
│  │  │ (aiohttp)  │  │ (PyMuPDF)  │  │ (BeautifulSoup)│  │    │
│  │  └────────────┘  └────────────┘  └────────────────┘  │    │
│  │  ┌────────────┐  ┌────────────┐                      │    │
│  │  │ API Client │  │ RSS/Atom   │                      │    │
│  │  │ (REST/SOAP)│  │ Parser     │                      │    │
│  │  └────────────┘  └────────────┘                      │    │
│  └──────────────────────────┬───────────────────────────┘    │
│                             │                                │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │              Change Detection Layer                   │    │
│  │                                                      │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │    │
│  │  │ Content    │  │ Diff       │  │ Version        │  │    │
│  │  │ Hash       │  │ Calculator │  │ Manager        │  │    │
│  │  │ Comparator │  │            │  │                │  │    │
│  │  └────────────┘  └────────────┘  └────────────────┘  │    │
│  └──────────────────────────┬───────────────────────────┘    │
│                             │                                │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │              Source Health Monitor                     │    │
│  │                                                      │    │
│  │  • Track source uptime/downtime                       │    │
│  │  • Alert on source unavailability                     │    │
│  │  • Measure crawl success rate                         │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────┬───────────────────────────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
    ┌──────────────┐  ┌────────────┐  ┌──────────────┐
    │ Chunks       │  │ Gov Data   │  │ Raw Data     │
    │ Engine       │  │ Sync       │  │ Store        │
    └──────────────┘  └────────────┘  └──────────────┘
```

---

## 4. Data Models

### 4.1 Fetched Document Record

```json
{
  "fetch_id": "uuid",
  "source_id": "gazette_india",
  "source_url": "https://egazette.gov.in/WriteReadData/2026/...",
  "fetch_timestamp": "2026-02-26T10:00:00Z",
  "document_type": "gazette_notification",
  "format": "pdf",
  "content_hash": "sha256:abcdef...",
  "content_size_bytes": 125000,
  "storage_path": "s3://raw-policies/gazette/2026/02/notification_1234.pdf",
  
  "extracted_metadata": {
    "title": "Amendment to PM-KISAN Guidelines",
    "ministry": "Agriculture and Farmers Welfare",
    "notification_number": "GOI/2026/AGR/1234",
    "publication_date": "2026-02-25",
    "effective_date": "2026-04-01",
    "states_affected": ["ALL"],
    "policy_id": "PM-KISAN-2024"
  },
  
  "change_detection": {
    "is_new": false,
    "previous_version_hash": "sha256:xyz...",
    "change_type": "amendment",
    "change_summary": "Income threshold increased from 2L to 3L",
    "diff_path": "s3://raw-policies/diffs/PM-KISAN-2024_v3_to_v4.json"
  },
  
  "processing_status": "sent_to_chunks_engine",
  "next_crawl_scheduled": "2026-02-27T10:00:00Z"
}
```

### 4.2 Source Configuration

```yaml
sources:
  - id: gazette_india
    name: "Gazette of India"
    url: "https://egazette.gov.in/"
    type: scraper
    schedule: "*/30 * * * *"    # Every 30 minutes
    parser: gazette_parser
    selectors:
      notification_list: "table.notification-list tr"
      pdf_link: "a.pdf-download"
    rate_limit: 1 req/sec
    
  - id: data_gov_in
    name: "data.gov.in"
    url: "https://api.data.gov.in/resource/"
    type: api
    schedule: "0 */6 * * *"    # Every 6 hours
    auth:
      type: api_key
      key_env: "DATA_GOV_API_KEY"
    rate_limit: 5 req/sec
    
  - id: pmkisan_portal
    name: "PM-KISAN Portal"
    url: "https://pmkisan.gov.in/"
    type: scraper
    schedule: "0 0 * * *"      # Daily
    parser: pmkisan_parser
    
  - id: rbi_notifications
    name: "RBI Notifications"
    url: "https://www.rbi.org.in/scripts/BS_CircularIndexDisplay.aspx"
    type: scraper
    schedule: "0 */4 * * *"    # Every 4 hours
    parser: rbi_parser
```

---

## 5. Context Flow

```
Scheduled crawl triggers (or webhook received)
    │
    ├─► Crawler Manager selects source
    │       │
    │       ├─► Rate limit check (respect source limits)
    │       └─► Fetch content (HTTP GET / API call)
    │
    ├─► Fetch & Parse Layer
    │       │
    │       ├─► Download document (PDF, HTML, JSON)
    │       ├─► Parse content (extract text, structure)
    │       ├─► Extract metadata (title, dates, ministry)
    │       └─► Generate content hash
    │
    ├─► Change Detection
    │       │
    │       ├─► Compare content_hash with stored version
    │       ├─► If unchanged → Skip (no event)
    │       ├─► If new → Store full content
    │       └─► If changed → Calculate diff, store delta
    │
    ├─► Version Management
    │       │
    │       ├─► Increment policy version
    │       ├─► Store change record with amendment reference
    │       └─► Archive previous version
    │
    └─► Output
            │
            ├─► Publish DOCUMENT_FETCHED event → Chunks Engine
            ├─► Publish POLICY_UPDATED event → Gov Data Sync Engine
            ├─► Log to Raw Data Store
            └─► Update source health metrics
```

---

## 6. Event Bus Integration

| Event Published | Consumers | Description |
|---|---|---|
| `DOCUMENT_FETCHED` | Chunks Engine | New document ready for chunking |
| `DOCUMENT_UPDATED` | Chunks Engine, Gov Data Sync | Policy amendment detected |
| `POLICY_VERSION_CREATED` | Vector DB, AI Core | New policy version available |
| `SOURCE_UNAVAILABLE` | Anomaly Detection, Admin | Data source down |
| `CRAWL_COMPLETED` | Analytics Warehouse | Crawl metrics |

---

## 7. NVIDIA Stack Alignment

| Component | NVIDIA Tool | Purpose |
|---|---|---|
| PDF text extraction | — | CPU-based (PyMuPDF) |
| OCR for scanned PDFs | NVIDIA cuOCR | GPU-accelerated OCR |
| Language detection | NVIDIA Riva | Detect document language |
| Entity extraction | NeMo NER | Extract dates, ministry names from text |

---

## 8. Scaling Strategy

| Scale Tier | Sources | Strategy |
|---|---|---|
| **Tier 1** (MVP) | < 20 sources | Single crawler, sequential |
| **Tier 2** | 20 – 100 sources | Async crawlers (aiohttp), parallel fetching |
| **Tier 3** | 100 – 500 sources | Distributed crawler pool, source-level sharding |
| **Tier 4** | 500+ sources | Regional crawler nodes, intelligent scheduling |

---

## 9. Policy Versioning Schema

```sql
CREATE TABLE policy_versions (
    policy_id           VARCHAR(64) NOT NULL,
    version             INTEGER NOT NULL,
    effective_date      DATE NOT NULL,
    expiry_date         DATE,
    amendment_reference VARCHAR(255),
    content_hash        VARCHAR(128) NOT NULL,
    storage_path        VARCHAR(512) NOT NULL,
    source_url          VARCHAR(1024),
    fetched_at          TIMESTAMP NOT NULL,
    status              VARCHAR(20) DEFAULT 'active',
    PRIMARY KEY (policy_id, version)
);

CREATE INDEX idx_policy_status ON policy_versions(policy_id, status);
CREATE INDEX idx_policy_effective ON policy_versions(effective_date);
```

---

## 10. API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/fetch/trigger` | Manually trigger a crawl |
| `GET` | `/api/v1/fetch/sources` | List all configured sources |
| `GET` | `/api/v1/fetch/sources/{id}/status` | Source health status |
| `GET` | `/api/v1/fetch/history` | Recent fetch history |
| `GET` | `/api/v1/fetch/policies/{policy_id}/versions` | Policy version history |
| `POST` | `/api/v1/fetch/sources` | Add new data source |
| `PUT` | `/api/v1/fetch/sources/{id}` | Update source configuration |

---

## 11. Dependencies

| Dependency | Direction | Purpose |
|---|---|---|
| **Government Websites** | External | Data source |
| **Chunks Engine** | Downstream | Sends fetched documents for chunking |
| **Gov Data Sync Engine** | Downstream | Notifies about policy changes |
| **Raw Data Store** | Downstream | Stores fetched document archives |
| **Event Bus** | Downstream | Publishes fetch events |
| **Document Understanding Engine** | Downstream | Complex document parsing |

---

## 12. Technology Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11 (FastAPI) |
| Async HTTP | aiohttp / httpx |
| HTML Scraping | BeautifulSoup4 + lxml |
| PDF Parsing | PyMuPDF / pdfplumber |
| Scheduling | APScheduler / Celery Beat |
| Change Detection | difflib + custom hash comparison |
| Storage | S3 / MinIO for document archives |
| Event Bus | Apache Kafka |
| Monitoring | Prometheus + custom crawl metrics |
| Containerization | Docker + Kubernetes |

---

## 13. Implementation Phases

| Phase | Milestone | Timeline |
|---|---|---|
| **Phase 1** | Basic scraper for 5 central government sources | Week 1-3 |
| **Phase 2** | PDF parsing, metadata extraction | Week 4-5 |
| **Phase 3** | Change detection, versioning | Week 6-7 |
| **Phase 4** | Scheduled crawling (APScheduler) | Week 8 |
| **Phase 5** | Expand to 20+ sources (state portals) | Week 9-11 |
| **Phase 6** | Webhook integration, data.gov.in API | Week 12-13 |
| **Phase 7** | Source health monitoring, alerting | Week 14-15 |

---

## 14. Ethical & Legal Considerations

| Concern | Mitigation |
|---|---|
| **robots.txt compliance** | Respect all robots.txt directives |
| **Rate limiting** | Conservative rate limits (1-5 req/sec) |
| **Government ToS** | Comply with terms of service of all portals |
| **Data accuracy** | Content hash verification, no modification of source data |
| **Attribution** | Always store and display source URL |

---

## 15. Success Metrics

| Metric | Target |
|---|---|
| Source coverage | > 100 government portals |
| Fetch success rate | > 95% |
| Change detection latency | < 1 hour from publication |
| Content extraction accuracy | > 95% |
| Policy version tracking completeness | 100% |
| Source uptime monitoring | 24/7 |

---

## 16. Official Data Sources (MVP)

| Data Required | Official Source | URL | Notes |
|---|---|---|---|
| Central govt schemes, CSV datasets, scheme lists | Open Government Data Portal (India) | https://data.gov.in | Primary structured data source — CSV, JSON, API |
| Policy announcements, daily official updates | Press Information Bureau (PIB) | https://pib.gov.in | Daily press releases, scheme announcements |
| Acts, amendments, legal texts | India Code | https://www.indiacode.nic.in | Full text of Indian legislation |
| Gazette notifications, official amendments | eGazette | https://egazette.nic.in | Source of truth for legal policy changes |
| Govt programs overview, policy summaries | MyGov | https://www.mygov.in | Citizen-facing program descriptions |
| Ministry-level scheme guidelines | India Portal | https://www.india.gov.in | National portal aggregating ministry data |
| State-level schemes and portals | State Govt Portals | https://www.india.gov.in/states | Per-state government data access |

### MVP Priority (Minimum Viable Crawl Set)

For the MVP launch, prioritize these 6 sources:
1. **data.gov.in** — structured scheme datasets
2. **PIB** — daily policy announcement feed
3. **India Code** — legal text for eligibility rules
4. **eGazette** — amendment and notification tracking
5. **Income Tax Portal** (https://www.incometax.gov.in) — tax-related policies
6. **Census India** (https://censusindia.gov.in) — demographic reference data
