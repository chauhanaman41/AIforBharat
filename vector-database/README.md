# Engine 6 — Vector Database

> In-memory vector index with cosine similarity search, backed by SQLite.

| Property | Value |
|----------|-------|
| **Port** | 8006 |
| **Folder** | `vector-database/` |
| **Database Tables** | `vector_records` |
| **Embedding Dim** | 1024 (NVIDIA nv-embedqa-e5-v5) |

## Run

```bash
uvicorn vector-database.main:app --port 8006 --reload
```

Docs: http://localhost:8006/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/vectors/upsert` | Insert/update vector (auto-embeds text via NIM) |
| POST | `/vectors/upsert/batch` | Batch upsert multiple vectors |
| POST | `/vectors/search` | Semantic search by text query |
| POST | `/vectors/search/embedding` | Search by pre-computed embedding vector |
| DELETE | `/vectors/{vector_id}` | Delete a single vector |
| DELETE | `/vectors/document/{document_id}` | Delete all vectors for a document |
| GET | `/vectors/stats` | Index statistics (total vectors, dimensions) |

## Architecture

- **In-Memory Index**: `LocalVectorIndex` class holds all vectors in memory for fast cosine similarity
- **SQLite Persistence**: Vectors stored as binary-packed floats in `vector_records` table
- **Auto-Embedding**: Text content is automatically embedded via NVIDIA NIM on upsert
- **Fallback**: If NIM API is unreachable, uses SHA-256 hash-based deterministic embeddings

## Request Models

- `UpsertVectorRequest` — `id`, `content` (text), `document_id`, `metadata` (dict)
- `BatchUpsertRequest` — `vectors` (list of upsert requests)
- `SearchRequest` — `query` (text), `top_k`, `min_score`
- `SearchByEmbeddingRequest` — `embedding` (float list), `top_k`, `min_score`

## Usage in Platform

The Chunks Engine (10) creates document chunks → Vector Database stores embeddings → Neural Network Engine (7) performs RAG queries against the index.

## Gateway Route

Not directly exposed via gateway. Used internally by the policy ingestion pipeline.

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **RAG Query** | `POST /api/v1/query` | Semantic vector search for context passages | Step 2 of 6 |
| **Policy Ingestion** | `POST /api/v1/ingest-policy` | Upsert embedding vectors for new policy chunks | Step 5 of 7 |
| **Voice Query** | `POST /api/v1/voice-query` | Vector search when intent is `scheme_query` | Conditional |

### Flow Detail: RAG Query

```
E7 (Intent) → E6 (Vector Search) → E7 (RAG Generate) → E8 ∥ E19 (Anomaly + Trust) → Audit
```

E6 searches the vector index using the user's query and returns the top-K most relevant policy chunks. These become the context passages fed to E7 for grounded generation.

### Flow Detail: Policy Ingestion

```
E11 (Fetch) → E21 (Parse) → E10 (Chunk) → E7 (Embed) → E6 (Vector Upsert)
  → E4 (Tag Metadata) → E3+E13 (Audit)
```

E6 receives embedding vectors from E7 and upserts them into the index, making the newly ingested policy searchable via RAG.

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/vectors/search` during RAG and voice queries |
| **Called by** | API Gateway (Orchestrator) | `/vectors/upsert/batch` during policy ingestion |
| **Fed by** | Neural Network (E7) | Embedding vectors for new policy chunks |
| **Fed by** | Chunks Engine (E10) | Chunk metadata (IDs, content, document references) |
| **Feeds** | Neural Network (E7) | Retrieved context passages for RAG generation |

## Shared Module Dependencies

- `shared/config.py` — `settings` (embedding model, embedding dimensions, port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`
- `shared/nvidia_client.py` — `nvidia_client` (auto-embedding on upsert)
- `shared/utils.py` — `generate_id()`, `sha256_hash()`
- `shared/cache.py` — `LocalCache`
