# Engine 10 — Chunks Engine

> Splits policy documents into semantic chunks for vector indexing.

| Property | Value |
|----------|-------|
| **Port** | 8010 |
| **Folder** | `chunks-engine/` |
| **Database Tables** | `document_chunks` |

## Run

```bash
uvicorn chunks-engine.main:app --port 8010 --reload
```

Docs: http://localhost:8010/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/chunks/create` | Split document into chunks |
| POST | `/chunks/batch` | Batch chunk multiple documents |
| GET | `/chunks/document/{document_id}` | Get all chunks for a document |
| GET | `/chunks/{chunk_id}` | Get a specific chunk |
| POST | `/chunks/rechunk` | Re-chunk with different strategy/size |
| GET | `/chunks/stats` | Chunking statistics |

## Chunking Strategies

| Strategy | Description |
|----------|-------------|
| `fixed` | Fixed size with overlap (default: 512 chars, 64 overlap) |
| `sentence` | Split on sentence boundaries (`.`, `?`, `!`) |
| `section` | Split on section headers (`#`, numbered sections) |
| `paragraph` | Split on double newlines |

## Configuration

| Parameter | Default | Range |
|-----------|---------|-------|
| `chunk_size` | 512 | 50 – 2000 |
| `overlap` | 64 | 0 – chunk_size/2 |
| `strategy` | `fixed` | fixed / sentence / section / paragraph |

## Request Models

- `ChunkRequest` — `document_id`, `content`, `strategy`, `chunk_size`, `overlap`, `metadata`
- `BatchChunkRequest` — `documents` (list of ChunkRequest)
- `ReChunkRequest` — `document_id`, `strategy`, `chunk_size`, `overlap`

## Pipeline Role

```
Engine 11 (fetch policy) → Engine 21 (parse) → Engine 10 (chunk) → Engine 6 (embed & index)
```

## Gateway Route

Not directly exposed via gateway. Used internally by the policy ingestion pipeline.

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **Policy Ingestion** | `POST /api/v1/ingest-policy` | Split parsed policy text into semantic chunks | Step 3 of 7 |

### Flow Detail: Policy Ingestion

```
E11 (Fetch) → E21 (Parse) → E10 (Chunk) → E7 (Embed) → E6 (Vector Upsert)
  → E4 (Tag Metadata) → E3+E13 (Audit)
```

E10 receives the full parsed text from E21 and splits it into overlapping chunks (default: 512 chars, 64 overlap, sentence strategy). The chunks are then sent to E7 for embedding and E6 for vector storage. If chunking fails, the pipeline returns a **partial ingestion** result.

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/chunks/create` during policy ingestion |
| **Fed by** | Policy Fetching (E11) | Raw document text |
| **Fed by** | Doc Understanding (E21) | Parsed/cleaned text |
| **Feeds** | Neural Network (E7) | Chunk texts for embedding generation |
| **Feeds** | Vector Database (E6) | Chunk metadata (IDs, content) for vector upsert |

## Shared Module Dependencies

- `shared/config.py` — `settings` (port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`
- `shared/event_bus.py` — `event_bus`
- `shared/utils.py` — `generate_id()`, `sha256_hash()`
