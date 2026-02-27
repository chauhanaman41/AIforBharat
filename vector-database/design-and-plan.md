# 🟦 Vector Database — Design & Plan

## 1. Purpose

The Vector Database is the **semantic knowledge backbone** of the AIforBharat platform. It stores dense vector embeddings of all government policies, schemes, budget speeches, circulars, gazette notifications, FAQs, and state-level updates — enabling **intelligent semantic search and Retrieval-Augmented Generation (RAG)**.

When a user asks *"Am I eligible for any housing scheme in UP?"*, this database finds the most relevant policy chunks through vector similarity, feeding context to the AI Core for accurate, grounded responses.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Policy Embeddings** | Dense vector representations of every policy document |
| **Semantic Search** | Find relevant policies by meaning, not just keywords |
| **Hybrid Search** | Combine BM25 (keyword) + vector (semantic) search |
| **FAQ Matching** | Match user questions to pre-embedded FAQ answers |
| **Contextual RAG** | Retrieve relevant context for LLM grounding |
| **Multi-Language Support** | Embeddings for Hindi, English, and regional languages |
| **Partitioned Storage** | Partition by state, ministry, year for efficient retrieval |
| **Real-Time Updates** | New policies indexed within minutes of ingestion |
| **Metadata Filtering** | Filter vectors by state, department, date range |
| **Versioned Embeddings** | Track embedding model version for re-indexing |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Content Sources                            │
│                                                              │
│  Chunks Engine │ Policy Fetcher │ Gov Data Sync │ Doc Engine │
└────────────────────────────┬─────────────────────────────────┘
                             │ Chunked + tagged documents
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    Vector Database System                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Embedding Pipeline                       │    │
│  │                                                      │    │
│  │  ┌──────────────┐  ┌──────────────┐                  │    │
│  │  │ NV-Embed-QA  │  │ Multilingual │                  │    │
│  │  │ (English)    │  │ Embed Model  │                  │    │
│  │  │              │  │ (Hindi/Indic)│                  │    │
│  │  └──────┬───────┘  └──────┬───────┘                  │    │
│  │         │                 │                           │    │
│  │         └────────┬────────┘                           │    │
│  │                  │ 768/1024-dim vectors                │    │
│  │                  ▼                                    │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Vector Store (Milvus / Qdrant / Weaviate)│    │
│  │                                                      │    │
│  │  ┌─────────────────────────────────────────────────┐ │    │
│  │  │  Collection: government_policies                 │ │    │
│  │  │                                                 │ │    │
│  │  │  Partitions:                                    │ │    │
│  │  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │ │    │
│  │  │  │ UP   │ │ MH   │ │ KA   │ │ CENTRAL│        │ │    │
│  │  │  └──────┘ └──────┘ └──────┘ └──────┘          │ │    │
│  │  │                                                 │ │    │
│  │  │  Indexes: IVF_FLAT / HNSW                       │ │    │
│  │  └─────────────────────────────────────────────────┘ │    │
│  │                                                      │    │
│  │  ┌─────────────────────────────────────────────────┐ │    │
│  │  │  Collection: faqs                               │ │    │
│  │  │  Collection: budget_speeches                    │ │    │
│  │  │  Collection: gazette_notifications              │ │    │
│  │  │  Collection: circulars                          │ │    │
│  │  └─────────────────────────────────────────────────┘ │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              BM25 Index (Elasticsearch / Tantivy)     │    │
│  │                                                      │    │
│  │  Keyword search layer for hybrid retrieval            │    │
│  │  Synchronized with vector collections                 │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Hybrid Search Engine                     │    │
│  │                                                      │    │
│  │  Score = α × vector_score + (1-α) × bm25_score       │    │
│  │  α dynamically adjusted per query type                │    │
│  │  Reciprocal Rank Fusion for result merging            │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Vector Schema

```json
{
  "collection": "government_policies",
  "schema": {
    "id": "chunk_uuid",
    "vector": "[768-dimensional float array]",
    "metadata": {
      "policy_id": "string",
      "policy_name": "string",
      "version": "integer",
      "state": "string",
      "ministry": "string",
      "department": "string",
      "effective_date": "date",
      "expiry_date": "date",
      "target_demographic": "string[]",
      "chunk_index": "integer",
      "total_chunks": "integer",
      "language": "string",
      "source_url": "string",
      "last_updated": "timestamp",
      "embedding_model": "string",
      "embedding_version": "string"
    },
    "text": "string (original chunk text)"
  },
  "index": {
    "type": "HNSW",
    "metric": "COSINE",
    "M": 16,
    "ef_construction": 256
  },
  "partition_key": "state"
}
```

---

## 4. Content Types Stored

| Content Type | Source | Update Frequency | Partition |
|---|---|---|---|
| **Central Government Schemes** | Policy Fetching Engine | On amendment | `CENTRAL` |
| **State Government Schemes** | Policy Fetching Engine | On amendment | State code |
| **Budget Speeches** | Gov Data Sync Engine | Annual | Year |
| **Gazette Notifications** | Gov Data Sync Engine | As published | Ministry |
| **Circulars & Orders** | Gov Data Sync Engine | As published | Department |
| **FAQs** | Manual + AI-generated | Weekly | Category |
| **Tax Rules** | Policy Fetching Engine | On amendment | `CENTRAL` |
| **Legal Acts** | Document Understanding | On amendment | Ministry |

---

## 5. Context Flow

```
New policy chunk arrives (from Chunks Engine via Event Bus)
    │
    ├─► Embedding Pipeline
    │       │
    │       ├─► Select embedding model based on language
    │       │   ├─► English: NV-Embed-QA
    │       │   └─► Hindi/Indic: Multilingual model
    │       ├─► Generate embedding vector (768/1024 dimensions)
    │       ├─► Attach metadata (state, ministry, dates, demographics)
    │       └─► Output: {vector, metadata, text}
    │
    ├─► Index in Vector Store
    │       │
    │       ├─► Route to correct partition (by state)
    │       ├─► Upsert vector (create or update)
    │       ├─► Update HNSW index incrementally
    │       └─► Sync to BM25 index (Elasticsearch)
    │
    └─► Search Flow (query from AI Core)
            │
            ├─► Receive query: "housing schemes for low income in UP"
            ├─► Embed query using same model
            ├─► Parallel:
            │   ├─► Vector search (top-K by cosine similarity)
            │   └─► BM25 search (keyword matching)
            ├─► Reciprocal Rank Fusion (merge results)
            ├─► Apply metadata filters (state=UP, active=true)
            ├─► Re-rank results (optional cross-encoder)
            └─► Return top-N chunks with scores
```

---

## 6. Event Bus Integration

| Event Consumed | Source | Action |
|---|---|---|
| `CHUNKS_CREATED` | Chunks Engine | Embed and index new chunks |
| `CHUNKS_UPDATED` | Chunks Engine | Re-embed and update vectors |
| `POLICY_EXPIRED` | Gov Data Sync | Mark vectors as expired (don't delete) |
| `POLICY_REPEALED` | Gov Data Sync | Flag vectors, deprioritize in search |
| `REINDEX_REQUESTED` | Admin | Full re-indexing with new model |

| Event Published | Consumers |
|---|---|
| `VECTORS_INDEXED` | AI Core (ready for RAG) |
| `SEARCH_COMPLETED` | Raw Data Store (logging) |
| `INDEX_HEALTH_ALERT` | Anomaly Detection |

---

## 7. NVIDIA Stack Alignment

| Component | NVIDIA Tool | Usage |
|---|---|---|
| **Embedding Model** | NV-Embed-QA (via NIM) | Enterprise-grade Q&A embeddings |
| **Embedding Inference** | Triton Inference Server | High-throughput embedding generation |
| **GPU Acceleration** | CUDA | Accelerated similarity computation |
| **Re-ranking** | NeMo Retriever | Cross-encoder re-ranking for precision |
| **Batch Embedding** | TensorRT | Optimized batch embedding generation |

---

## 8. Scaling Strategy

| Scale Tier | Vectors | Strategy |
|---|---|---|
| **Tier 1** (MVP) | < 100K | Single Milvus/Qdrant instance, CPU search |
| **Tier 2** | 100K – 5M | GPU-accelerated search, HNSW index |
| **Tier 3** | 5M – 50M | Distributed Milvus cluster, partitioned by state |
| **Tier 4** | 50M+ | Multi-region clusters, tiered indexing, edge caching |

### Partitioning Strategy

```
Partition by State (36 partitions):
    UP, MH, KA, TN, ... CENTRAL

Within each partition, filter by:
    Ministry → Department → Year → Status (active/expired)
```

### Key Decisions

- **Index type**: HNSW for online queries (low latency), IVF_FLAT for batch
- **Hybrid search weight**: α = 0.7 (vector) for semantic queries, α = 0.3 for keyword-heavy
- **Embedding dimension**: 768 (NV-Embed-QA) — balance of quality and storage
- **Replica factor**: 2 (for high availability)
- **Refresh strategy**: Incremental updates, full re-index monthly

---

## 9. API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/vectors/search` | Semantic search with optional filters |
| `POST` | `/api/v1/vectors/hybrid-search` | Combined vector + BM25 search |
| `POST` | `/api/v1/vectors/embed` | Generate embedding for text |
| `POST` | `/api/v1/vectors/upsert` | Insert/update vectors |
| `DELETE` | `/api/v1/vectors/{chunk_id}` | Remove vector (soft delete) |
| `GET` | `/api/v1/vectors/collections` | List all collections |
| `GET` | `/api/v1/vectors/stats` | Collection statistics |
| `POST` | `/api/v1/vectors/reindex` | Trigger re-indexing (admin) |

### Search Request Example

```json
{
  "query": "housing scheme for low income families",
  "filters": {
    "state": ["UP", "CENTRAL"],
    "status": "active",
    "effective_date_before": "2026-03-01"
  },
  "top_k": 10,
  "search_type": "hybrid",
  "alpha": 0.7,
  "include_metadata": true,
  "include_text": true
}
```

---

## 10. Dependencies

| Dependency | Direction | Purpose |
|---|---|---|
| **Chunks Engine** | Upstream | Provides chunked, tagged policy text |
| **Document Understanding Engine** | Upstream | Provides structured document extractions |
| **AI Core (Neural Network)** | Downstream | Queries for RAG context |
| **Anomaly Detection** | Downstream | Validates retrieval quality |
| **Embedding Model (NV-Embed-QA)** | External | Generates vector embeddings |
| **Triton Inference Server** | External | Hosts embedding model |

---

## 11. Technology Stack

| Layer | Technology |
|---|---|
| Vector Store | Milvus 2.x / Qdrant / Weaviate |
| BM25 Index | Elasticsearch 8.x / Tantivy |
| Embedding Model | NV-Embed-QA (NVIDIA NIM) |
| Inference Server | Triton Inference Server |
| Re-ranker | NeMo Retriever cross-encoder |
| Data Format | Float32 vectors, JSON metadata |
| Monitoring | Grafana + custom vector DB metrics |
| Containerization | Docker + Kubernetes (StatefulSet) |

---

## 12. Implementation Phases

| Phase | Milestone | Timeline |
|---|---|---|
| **Phase 1** | Milvus/Qdrant setup, basic embedding pipeline | Week 1-2 |
| **Phase 2** | NV-Embed-QA integration via Triton | Week 3-4 |
| **Phase 3** | Hybrid search (BM25 + vector), metadata filtering | Week 5-6 |
| **Phase 4** | Partitioning by state, incremental indexing | Week 7-8 |
| **Phase 5** | Cross-encoder re-ranking, multilingual embeddings | Week 9-10 |
| **Phase 6** | GPU-accelerated search, distributed cluster | Week 12-14 |

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Search latency (P95) | < 100ms |
| Recall@10 | > 0.85 |
| MRR (Mean Reciprocal Rank) | > 0.75 |
| Embedding throughput | > 500 docs/sec |
| Index freshness (new policy → searchable) | < 5 minutes |
| Hybrid search improvement over vector-only | > 10% on precision |

---

## 14. Security Hardening

### 14.1 Rate Limiting

<!-- SECURITY: Vector search powers the RAG pipeline — rate limits prevent
     embedding generation abuse and search DoS.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  # SECURITY: Vector search — primary RAG query path
  "/api/v1/vectors/search":
    per_user:
      requests_per_minute: 30
      burst: 10
    per_ip:
      requests_per_minute: 20

  # SECURITY: Hybrid search (vector + keyword)
  "/api/v1/vectors/hybrid-search":
    per_user:
      requests_per_minute: 20
      burst: 5

  # SECURITY: Vector upsert — internal only (from Chunks Engine)
  "/api/v1/vectors/upsert":
    per_service:
      requests_per_minute: 500
    allowed_callers: ["chunks-engine", "document-understanding-engine"]

  # SECURITY: Collection management — admin only
  "/api/v1/vectors/collections":
    per_user:
      requests_per_minute: 5
    require_role: admin

  # SECURITY: Index rebuild — heavy operation
  "/api/v1/vectors/reindex":
    per_user:
      requests_per_hour: 2
    require_role: admin

  rate_limit_response:
    status: 429
    body:
      error: "rate_limit_exceeded"
      message: "Vector search rate limit reached."
```

### 14.2 Input Validation & Sanitization

<!-- SECURITY: Vector search queries accept text that gets embedded.
     Validation prevents embedding injection and resource abuse.
     OWASP Reference: API3:2023, API8:2023 -->

```python
# SECURITY: Vector search schema
VECTOR_SEARCH_SCHEMA = {
    "type": "object",
    "required": ["query"],
    "additionalProperties": False,
    "properties": {
        "query": {
            "type": "string",
            "minLength": 2,
            "maxLength": 1000,
            "description": "Natural language search query"
        },
        "top_k": {
            "type": "integer",
            "minimum": 1,
            "maximum": 50,
            "default": 10
        },
        "filters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "scheme_id": {"type": "string", "pattern": "^sch_[a-zA-Z0-9]+$"},
                "source_type": {"type": "string", "enum": ["gazette","notification","circular","guideline","faq","amendment"]},
                "language": {"type": "string", "enum": ["en","hi","bn","te","mr","ta","gu","kn"]},
                "min_date": {"type": "string", "format": "date"},
                "max_date": {"type": "string", "format": "date"}
            }
        },
        "similarity_threshold": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "default": 0.7
        }
    }
}

# SECURITY: Vector upsert validation — internal only
VECTOR_UPSERT_SCHEMA = {
    "type": "object",
    "required": ["vectors"],
    "additionalProperties": False,
    "properties": {
        "vectors": {
            "type": "array",
            "maxItems": 100,  # Batch limit
            "items": {
                "type": "object",
                "required": ["id", "embedding", "metadata"],
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string", "pattern": "^vec_[a-zA-Z0-9]+$"},
                    "embedding": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 768,  # Expected embedding dimension
                        "maxItems": 1024
                    },
                    "metadata": {
                        "type": "object",
                        "maxProperties": 20
                    }
                }
            }
        }
    }
}

# SECURITY: Embedding dimension validation
def validate_embedding(embedding: list, expected_dim: int = 768) -> bool:
    """Ensure embedding has correct dimensionality and valid values."""
    if len(embedding) != expected_dim:
        return False
    if any(not isinstance(v, (int, float)) for v in embedding):
        return False
    # Check for NaN or Inf values
    import math
    if any(math.isnan(v) or math.isinf(v) for v in embedding):
        return False
    return True
```

### 14.3 Secure API Key & Secret Management

```yaml
secrets_management:
  environment_variables:
    - MILVUS_ROOT_PASSWORD      # Milvus admin password
    - MILVUS_API_KEY            # Milvus API authentication
    - NIM_API_KEY               # NVIDIA NIM for embedding generation
    - KAFKA_SASL_PASSWORD       # Event bus auth
    - REDIS_PASSWORD            # Query result cache
    - S3_ACCESS_KEY_ID          # Vector backup storage
    - S3_SECRET_ACCESS_KEY      # Vector backup storage

  rotation_policy:
    milvus_credentials: 90_days
    nim_api_key: 180_days
    s3_credentials: 90_days

  # SECURITY: Vector DB contains policy embeddings only — no PII
  data_policy:
    no_pii_in_embeddings: true
    embedding_source_text_not_stored: true  # Only vectors, not original text
    backup_encryption: AES-256
```

### 14.4 OWASP Compliance

| OWASP Risk | Mitigation |
|---|---|
| **API1: BOLA** | Vector data is public policy — no user ownership; admin-only for mutations |
| **API2: Broken Auth** | Search requires valid JWT; upsert requires service token; admin for collections |
| **API3: Broken Property Auth** | `additionalProperties: false`; top_k and filter enums validated |
| **API4: Resource Consumption** | top_k capped at 50; batch upsert capped at 100; reindex rate-limited |
| **API5: Broken Function Auth** | Collection management and reindex admin-only |
| **API6: Sensitive Flows** | No PII in vectors; embeddings are irreversible |
| **API7: SSRF** | No URL inputs; queries are text strings only |
| **API8: Misconfig** | Milvus behind VPC; no public access; TLS required |
| **API9: Improper Inventory** | Collection and index versions tracked; migration handled via CI/CD |
| **API10: Unsafe Consumption** | Embedding outputs validated for NaN/Inf; dimension checks enforced |
