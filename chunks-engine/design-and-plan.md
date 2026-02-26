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
