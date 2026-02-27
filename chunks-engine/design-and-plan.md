# 📄 Chunks Engine — Design & Plan

## 1. Purpose

The Chunks Engine breaks government policy documents into **semantic chunks** — meaningful, self-contained segments of text that can be independently embedded, retrieved, and cited. Each chunk is tagged with rich metadata (state, department, effective date, expiry date, target demographic) enabling precise, filtered retrieval.

**Core Mission:** Transform long, complex government documents into RAG-ready chunks that maximize retrieval precision and minimize hallucination risk.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Semantic Chunking** | Split documents by meaning, not just character count |
| **Metadata Tagging** | Auto-tag: state, department, effective date, expiry, demographic |
| **Hierarchical Chunking** | Maintain parent-child relationships between chunks |
| **Multi-Language Support** | Chunk Hindi, English, and regional language documents |
| **Overlap Management** | Configurable chunk overlap for context continuity |
| **Re-Chunking** | Auto re-chunk when policies are updated |
| **Deduplication** | Detect and merge duplicate/near-duplicate chunks |
| **Quality Scoring** | Score each chunk for completeness and coherence |
| **Async Ingestion** | Asynchronous pipeline for high-volume document processing |
| **Version Tracking** | Track which document version produced each chunk |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Input Sources                              │
│                                                              │
│  Policy Fetching │ Gov Data Sync │ Document Understanding    │
│  Engine          │ Engine        │ Engine                    │
└────────────────────────────┬─────────────────────────────────┘
                             │ Raw documents (PDF, HTML, text)
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                      Chunks Engine                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Pre-Processing Layer                     │    │
│  │                                                      │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │    │
│  │  │ PDF/HTML   │  │ Language   │  │ Section        │  │    │
│  │  │ Parser     │  │ Detector   │  │ Detector       │  │    │
│  │  │            │  │            │  │ (heading/para) │  │    │
│  │  └────────────┘  └────────────┘  └────────────────┘  │    │
│  └──────────────────────────┬───────────────────────────┘    │
│                             │                                │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │              Chunking Strategy Layer                   │    │
│  │                                                      │    │
│  │  ┌────────────────┐  ┌──────────────────────────┐    │    │
│  │  │ Semantic       │  │ Configurable Parameters  │    │    │
│  │  │ Chunker        │  │                          │    │    │
│  │  │                │  │ • chunk_size: 512 tokens  │    │    │
│  │  │ • Sentence     │  │ • overlap: 50 tokens     │    │    │
│  │  │   boundary     │  │ • min_chunk: 100 tokens   │    │    │
│  │  │ • Section      │  │ • max_chunk: 1024 tokens  │    │    │
│  │  │   boundary     │  │ • strategy: semantic      │    │    │
│  │  │ • Topic change │  │                          │    │    │
│  │  └────────────────┘  └──────────────────────────┘    │    │
│  └──────────────────────────┬───────────────────────────┘    │
│                             │                                │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │              Metadata Extraction Layer                 │    │
│  │                                                      │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │    │
│  │  │ State      │  │ Date       │  │ Demographic    │  │    │
│  │  │ Detector   │  │ Extractor  │  │ Tagger         │  │    │
│  │  │            │  │            │  │                │  │    │
│  │  │ NER for    │  │ Effective  │  │ Target group   │  │    │
│  │  │ state/dept │  │ & expiry   │  │ classification │  │    │
│  │  └────────────┘  └────────────┘  └────────────────┘  │    │
│  └──────────────────────────┬───────────────────────────┘    │
│                             │                                │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │              Output Layer                             │    │
│  │                                                      │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │    │
│  │  │ Quality    │  │ Dedup      │  │ Event          │  │    │
│  │  │ Scorer     │  │ Filter     │  │ Publisher      │  │    │
│  │  └────────────┘  └────────────┘  └────────────────┘  │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────┬───────────────────────────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
    ┌──────────────┐  ┌────────────┐  ┌──────────────┐
    │ Vector       │  │ Event Bus  │  │ Raw Data     │
    │ Database     │  │            │  │ Store        │
    └──────────────┘  └────────────┘  └──────────────┘
```

---

## 4. Data Models

### 4.1 Chunk Output

```json
{
  "chunk_id": "chk_uuid_v4",
  "document_id": "doc_uuid",
  "policy_id": "PM-KISAN-2024-v3",
  "chunk_index": 5,
  "total_chunks": 23,
  "parent_chunk_id": "chk_parent_uuid",
  
  "text": "Under PM-KISAN, all land-holding farmer families shall receive income support of Rs. 6,000 per year in three equal instalments...",
  "text_length_tokens": 487,
  "language": "en",
  
  "metadata": {
    "state": "CENTRAL",
    "ministry": "Agriculture and Farmers Welfare",
    "department": "Department of Agriculture",
    "effective_date": "2024-02-01",
    "expiry_date": null,
    "target_demographics": ["farmers", "land_holders"],
    "scheme_type": "direct_benefit_transfer",
    "section_heading": "Eligibility and Benefits",
    "source_url": "https://pmkisan.gov.in/guidelines_v3.pdf",
    "page_number": 4
  },
  
  "quality": {
    "completeness_score": 0.92,
    "coherence_score": 0.88,
    "standalone_readability": 0.85
  },
  
  "versioning": {
    "document_version": 3,
    "chunk_version": 1,
    "chunked_at": "2026-02-26T10:00:00Z",
    "chunking_model": "semantic_v2",
    "prev_chunk_id": null
  }
}
```

### 4.2 Chunking Configuration

```yaml
chunking_profiles:
  government_policy:
    strategy: semantic
    chunk_size_tokens: 512
    overlap_tokens: 50
    min_chunk_tokens: 100
    max_chunk_tokens: 1024
    split_on:
      - section_heading
      - numbered_clause
      - paragraph_break
    preserve:
      - tables
      - lists
      - definitions
      
  budget_speech:
    strategy: paragraph
    chunk_size_tokens: 300
    overlap_tokens: 30
    
  gazette_notification:
    strategy: semantic
    chunk_size_tokens: 400
    overlap_tokens: 40
```

---

## 5. Context Flow

```
Document arrives from Policy Fetching / Gov Data Sync Engine
    │
    ├─► Pre-Processing
    │       ├─► Parse format (PDF → text, HTML → text)
    │       ├─► Detect language (en/hi/regional)
    │       ├─► Detect sections (headings, clauses, tables)
    │       └─► Clean text (remove headers/footers, normalize whitespace)
    │
    ├─► Chunking
    │       ├─► Select chunking profile based on document type
    │       ├─► Apply semantic splitting (sentence/section boundaries)
    │       ├─► Ensure overlap between adjacent chunks
    │       ├─► Maintain parent-child hierarchy
    │       └─► Validate chunk sizes (within min/max bounds)
    │
    ├─► Metadata Extraction
    │       ├─► NER: Extract state, department, ministry names
    │       ├─► Date extraction: effective_date, expiry_date
    │       ├─► Demographic tagging: target population segments
    │       └─► Source tracking: URL, page number, section heading
    │
    ├─► Quality & Dedup
    │       ├─► Score each chunk for completeness and coherence
    │       ├─► Detect near-duplicate chunks (MinHash/SimHash)
    │       └─► Merge or flag duplicates
    │
    └─► Output
            ├─► Publish CHUNKS_CREATED event (Vector DB will embed)
            ├─► Log to Raw Data Store (processing audit)
            └─► Update chunk registry
```

---

## 6. Event Bus Integration

| Event Consumed | Source | Action |
|---|---|---|
| `DOCUMENT_FETCHED` | Policy Fetching Engine | Start chunking pipeline |
| `DOCUMENT_UPDATED` | Gov Data Sync Engine | Re-chunk updated document |
| `DOCUMENT_PARSED` | Document Understanding Engine | Chunk structured extraction |

| Event Published | Consumers |
|---|---|
| `CHUNKS_CREATED` | Vector Database (embed and index) |
| `CHUNKS_UPDATED` | Vector Database (re-embed) |
| `CHUNKS_DELETED` | Vector Database (remove vectors) |
| `CHUNKING_FAILED` | Anomaly Detection, Admin Dashboard |

---

## 7. NVIDIA Stack Alignment

| Component | NVIDIA Tool | Purpose |
|---|---|---|
| Semantic chunking NLP | NeMo BERT | Sentence boundary detection, topic segmentation |
| NER extraction | NeMo NER | State, department, date extraction |
| Batch processing | RAPIDS cuDF | GPU-accelerated text processing |
| Language detection | NVIDIA Riva | Identify document language |

---

## 8. Scaling Strategy

| Scale Tier | Documents/Day | Strategy |
|---|---|---|
| **Tier 1** (MVP) | < 100 | Single worker, synchronous processing |
| **Tier 2** | 100 – 10K | Async Kafka consumers, parallel chunking |
| **Tier 3** | 10K – 100K | Worker pool with GPU-accelerated NLP |
| **Tier 4** | 100K+ | Distributed chunking cluster, streaming pipeline |

---

## 9. API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/chunks/process` | Submit document for chunking |
| `GET` | `/api/v1/chunks/document/{doc_id}` | Get all chunks for a document |
| `GET` | `/api/v1/chunks/{chunk_id}` | Get specific chunk |
| `POST` | `/api/v1/chunks/rechunk/{doc_id}` | Trigger re-chunking |
| `GET` | `/api/v1/chunks/stats` | Chunking statistics |
| `DELETE` | `/api/v1/chunks/document/{doc_id}` | Remove all chunks for a document |

---

## 10. Dependencies

| Dependency | Direction | Purpose |
|---|---|---|
| **Policy Fetching Engine** | Upstream | Raw documents to chunk |
| **Gov Data Sync Engine** | Upstream | Updated documents to re-chunk |
| **Document Understanding Engine** | Upstream | Structured document extractions |
| **Vector Database** | Downstream | Chunks to embed and index |
| **Event Bus** | Bidirectional | Event-driven processing |
| **Raw Data Store** | Downstream | Audit logging |

---

## 11. Technology Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11 (FastAPI) |
| Chunking Library | LangChain TextSplitters + custom semantic splitter |
| NLP Models | NeMo BERT (sentence boundary, NER) |
| PDF Parsing | PyMuPDF (fitz) / pdfplumber |
| HTML Parsing | BeautifulSoup4 + trafilatura |
| Deduplication | datasketch (MinHash LSH) |
| Async Workers | Celery / ARQ |
| Event Bus | Apache Kafka |
| Containerization | Docker + Kubernetes |

---

## 12. Implementation Phases

| Phase | Milestone | Timeline |
|---|---|---|
| **Phase 1** | Basic fixed-size chunking, PDF/HTML parsing | Week 1-2 |
| **Phase 2** | Semantic chunking (sentence/section boundaries) | Week 3-4 |
| **Phase 3** | Metadata extraction (NER for state, dates) | Week 5-6 |
| **Phase 4** | Quality scoring, deduplication | Week 7-8 |
| **Phase 5** | Auto re-chunking on policy updates | Week 9-10 |
| **Phase 6** | Multilingual chunking, hierarchy support | Week 11-13 |

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Chunking throughput | > 100 documents/min |
| Chunk quality score (avg) | > 0.85 |
| Metadata extraction accuracy | > 90% |
| Duplicate detection rate | > 95% |
| Re-chunking latency | < 30s per document |
| Chunk-to-retrieval relevance | > 85% (measured via RAG eval) |

---

## 14. Security Hardening

### 14.1 Rate Limiting

<!-- SECURITY: Chunking is a backend/internal engine — primarily called by
     Document Understanding and Policy Fetching engines.
     Public endpoints are limited; internal endpoints rate-limited per service.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  # SECURITY: Manual re-chunking trigger — admin only
  "/api/v1/chunks/reprocess":
    per_user:
      requests_per_minute: 5
      burst: 2
    require_role: admin

  # SECURITY: Chunk search/retrieval — used by RAG pipeline
  "/api/v1/chunks/search":
    per_user:
      requests_per_minute: 60
      burst: 15
    per_ip:
      requests_per_minute: 30

  # SECURITY: Chunk metadata retrieval
  "/api/v1/chunks/{chunk_id}":
    per_user:
      requests_per_minute: 60

  # SECURITY: Internal ingestion endpoint
  internal_endpoints:
    "/internal/chunks/ingest":
      per_service:
        requests_per_minute: 200
      allowed_callers: ["document-understanding-engine", "policy-fetching-engine"]

  rate_limit_response:
    status: 429
    body:
      error: "rate_limit_exceeded"
      message: "Chunking service rate limit reached."
```

### 14.2 Input Validation & Sanitization

<!-- SECURITY: Chunks engine processes document text — must validate
     to prevent injection into vector embeddings.
     OWASP Reference: API3:2023, API8:2023 -->

```python
# SECURITY: Document ingestion schema
INGESTION_SCHEMA = {
    "type": "object",
    "required": ["document_id", "content", "source_type"],
    "additionalProperties": False,
    "properties": {
        "document_id": {
            "type": "string",
            "pattern": "^doc_[a-zA-Z0-9]{12,32}$"
        },
        "content": {
            "type": "string",
            "minLength": 10,
            "maxLength": 500000  # ~500KB text max
        },
        "source_type": {
            "type": "string",
            "enum": ["gazette", "notification", "circular", "guideline", "faq", "amendment"]
        },
        "metadata": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "scheme_id": {"type": "string", "pattern": "^sch_[a-zA-Z0-9]+$"},
                "language": {"type": "string", "enum": ["en", "hi", "bn", "te", "mr", "ta", "gu", "kn"]},
                "effective_date": {"type": "string", "format": "date"},
                "region": {"type": "string", "maxLength": 100}
            }
        }
    }
}

# SECURITY: Chunk search validation — prevent embedding injection
SEARCH_SCHEMA = {
    "type": "object",
    "required": ["query"],
    "additionalProperties": False,
    "properties": {
        "query": {"type": "string", "minLength": 2, "maxLength": 1000},
        "top_k": {"type": "integer", "minimum": 1, "maximum": 50},
        "filters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "scheme_id": {"type": "string"},
                "source_type": {"type": "string", "enum": ["gazette","notification","circular","guideline","faq","amendment"]},
                "min_date": {"type": "string", "format": "date"},
                "max_date": {"type": "string", "format": "date"}
            }
        }
    }
}
```

### 14.3 Secure API Key & Secret Management

```yaml
secrets_management:
  environment_variables:
    - DB_PASSWORD               # PostgreSQL (chunk metadata)
    - MILVUS_API_KEY            # Vector DB for embeddings
    - KAFKA_SASL_PASSWORD       # Event bus auth
    - NIM_API_KEY               # NVIDIA NIM for embedding generation
    - REDIS_PASSWORD            # Deduplication cache

  rotation_policy:
    db_credentials: 90_days
    milvus_key: 90_days
    nim_api_key: 180_days
```

### 14.4 OWASP Compliance

| OWASP Risk | Mitigation |
|---|---|
| **API1: BOLA** | Chunks are public policy data — no user-level ownership; admin-only for mutations |
| **API2: Broken Auth** | Internal ingestion requires service token; search requires valid JWT |
| **API3: Broken Property Auth** | `additionalProperties: false`; source_type enum validated |
| **API4: Resource Consumption** | Content size limits; top_k caps; internal throughput limits |
| **API5: Broken Function Auth** | Re-chunking and ingestion restricted to admin/internal callers |
| **API6: Sensitive Flows** | No PII in chunks — only policy text; no sensitive mutations |
| **API7: SSRF** | No URL inputs; content provided as plain text |
| **API8: Misconfig** | Chunking parameters (size, overlap) in config — not API-modifiable |
| **API9: Improper Inventory** | Chunk versions tracked; superseded chunks marked with lineage |
| **API10: Unsafe Consumption** | Embedding model outputs validated for dimensionality and NaN checks |
