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
