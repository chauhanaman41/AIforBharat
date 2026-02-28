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
