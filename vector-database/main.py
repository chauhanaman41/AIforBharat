"""
AIforBharat — Vector Database Engine (Engine 6)
=================================================
Local vector store for semantic search over policy chunks.
Stores NVIDIA NIM embeddings with cosine similarity search.
Uses in-memory FAISS-like index backed by SQLite persistence.

Port: 8006
"""

import logging, time, os, sys, json, math, struct
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, LargeBinary, select, delete, func

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.nvidia_client import nvidia_client
from shared.utils import generate_id
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("vector_database")
START_TIME = time.time()
search_cache = LocalCache(namespace="vector_search", ttl=600)

EMBEDDING_DIM = 1024  # NVIDIA NIM embedding dimension


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class VectorRecord(Base):
    __tablename__ = "vector_records"
    id = Column(String, primary_key=True, default=generate_id)
    chunk_id = Column(String, index=True)
    document_id = Column(String, index=True)
    policy_id = Column(String, index=True)
    content = Column(Text, nullable=False)
    embedding_blob = Column(LargeBinary)     # packed float32 array
    embedding_dim = Column(Integer, default=EMBEDDING_DIM)
    namespace = Column(String, default="policies", index=True)
    metadata_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── In-Memory Vector Index ───────────────────────────────────────────────────

class LocalVectorIndex:
    """
    In-memory vector index with cosine similarity search.
    Backed by SQLite for persistence.
    """

    def __init__(self):
        self.vectors: Dict[str, List[float]] = {}
        self.metadata: Dict[str, dict] = {}

    def add(self, vec_id: str, embedding: List[float], meta: dict = None):
        self.vectors[vec_id] = embedding
        self.metadata[vec_id] = meta or {}

    def remove(self, vec_id: str):
        self.vectors.pop(vec_id, None)
        self.metadata.pop(vec_id, None)

    def search(self, query_embedding: List[float], top_k: int = 5,
               namespace: str = None, min_score: float = 0.0) -> List[Tuple[str, float, dict]]:
        """Cosine similarity search."""
        if not self.vectors:
            return []

        results = []
        q_norm = math.sqrt(sum(x * x for x in query_embedding)) or 1e-10

        for vec_id, vec in self.vectors.items():
            if namespace and self.metadata.get(vec_id, {}).get("namespace") != namespace:
                continue

            dot = sum(a * b for a, b in zip(query_embedding, vec))
            v_norm = math.sqrt(sum(x * x for x in vec)) or 1e-10
            score = dot / (q_norm * v_norm)

            if score >= min_score:
                results.append((vec_id, score, self.metadata.get(vec_id, {})))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    @property
    def size(self):
        return len(self.vectors)


# Global index
vector_index = LocalVectorIndex()


def _pack_embedding(embedding: List[float]) -> bytes:
    """Pack float list to binary for storage."""
    return struct.pack(f'{len(embedding)}f', *embedding)


def _unpack_embedding(blob: bytes, dim: int = EMBEDDING_DIM) -> List[float]:
    """Unpack binary to float list."""
    return list(struct.unpack(f'{dim}f', blob))


# ── Schemas ───────────────────────────────────────────────────────────────────

class UpsertVectorRequest(BaseModel):
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None
    policy_id: Optional[str] = None
    content: str
    embedding: Optional[List[float]] = None  # Pre-computed, or will be generated
    namespace: str = "policies"
    metadata: dict = {}


class BatchUpsertRequest(BaseModel):
    vectors: List[UpsertVectorRequest]


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    namespace: str = "policies"
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    use_embedding: bool = True


class SearchByEmbeddingRequest(BaseModel):
    embedding: List[float]
    top_k: int = 5
    namespace: str = "policies"
    min_score: float = 0.0


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Vector Database starting...")
    await init_db()
    # Load existing vectors into memory index
    await _load_index()
    yield

app = FastAPI(title="AIforBharat Vector Database", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


async def _load_index():
    """Load all vectors from SQLite into in-memory index on startup."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(VectorRecord))).scalars().all()
        for row in rows:
            if row.embedding_blob:
                embedding = _unpack_embedding(row.embedding_blob, row.embedding_dim)
                vector_index.add(row.id, embedding, {
                    "chunk_id": row.chunk_id, "document_id": row.document_id,
                    "policy_id": row.policy_id, "content": row.content,
                    "namespace": row.namespace,
                    **(json.loads(row.metadata_json) if row.metadata_json else {}),
                })
    logger.info(f"Loaded {vector_index.size} vectors into in-memory index")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="vector_database", uptime_seconds=time.time() - START_TIME)


@app.post("/vectors/upsert", response_model=ApiResponse, tags=["Vectors"])
async def upsert_vector(data: UpsertVectorRequest):
    """
    Insert or update a vector. If no embedding provided, generates one
    using NVIDIA NIM embeddings API.
    
    Input: Content text + optional pre-computed embedding
    Output: Vector ID + confirmation
    """
    embedding = data.embedding
    if not embedding:
        try:
            embedding = await nvidia_client.generate_embedding(data.content)
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}; using hash-based fallback")
            # Fallback: create a deterministic pseudo-embedding from content hash
            import hashlib
            h = hashlib.sha512(data.content.encode()).digest()
            # Expand hash to EMBEDDING_DIM floats between -1 and 1
            embedding = []
            for i in range(EMBEDDING_DIM):
                byte_idx = i % len(h)
                embedding.append((h[byte_idx] / 127.5) - 1.0)

    vec_id = generate_id()

    # Store to DB
    async with AsyncSessionLocal() as session:
        record = VectorRecord(
            id=vec_id, chunk_id=data.chunk_id,
            document_id=data.document_id, policy_id=data.policy_id,
            content=data.content, embedding_blob=_pack_embedding(embedding),
            embedding_dim=len(embedding), namespace=data.namespace,
            metadata_json=json.dumps(data.metadata),
        )
        session.add(record)
        await session.commit()

    # Add to in-memory index
    vector_index.add(vec_id, embedding, {
        "chunk_id": data.chunk_id, "document_id": data.document_id,
        "policy_id": data.policy_id, "content": data.content,
        "namespace": data.namespace, **data.metadata,
    })

    return ApiResponse(message="Vector upserted", data={
        "vector_id": vec_id, "dimensions": len(embedding),
        "index_size": vector_index.size,
    })


@app.post("/vectors/upsert/batch", response_model=ApiResponse, tags=["Vectors"])
async def batch_upsert(data: BatchUpsertRequest):
    """Batch upsert multiple vectors."""
    # Generate embeddings for those without
    texts_to_embed = [v.content for v in data.vectors if not v.embedding]
    generated_embeddings = []
    if texts_to_embed:
        try:
            generated_embeddings = await nvidia_client.generate_embeddings_batch(texts_to_embed)
        except Exception as e:
            logger.warning(f"Batch embedding failed: {e}; using fallback")
            import hashlib
            for t in texts_to_embed:
                h = hashlib.sha512(t.encode()).digest()
                emb = [(h[i % len(h)] / 127.5) - 1.0 for i in range(EMBEDDING_DIM)]
                generated_embeddings.append(emb)

    gen_idx = 0
    inserted = 0

    async with AsyncSessionLocal() as session:
        for v in data.vectors:
            if v.embedding:
                embedding = v.embedding
            else:
                embedding = generated_embeddings[gen_idx] if gen_idx < len(generated_embeddings) else [0.0] * EMBEDDING_DIM
                gen_idx += 1

            vec_id = generate_id()
            record = VectorRecord(
                id=vec_id, chunk_id=v.chunk_id,
                document_id=v.document_id, policy_id=v.policy_id,
                content=v.content, embedding_blob=_pack_embedding(embedding),
                embedding_dim=len(embedding), namespace=v.namespace,
                metadata_json=json.dumps(v.metadata),
            )
            session.add(record)
            vector_index.add(vec_id, embedding, {
                "chunk_id": v.chunk_id, "document_id": v.document_id,
                "policy_id": v.policy_id, "content": v.content,
                "namespace": v.namespace, **v.metadata,
            })
            inserted += 1

        await session.commit()

    return ApiResponse(message=f"Batch upserted {inserted} vectors", data={
        "inserted": inserted, "index_size": vector_index.size,
    })


@app.post("/vectors/search", response_model=ApiResponse, tags=["Search"])
async def search_vectors(data: SearchRequest):
    """
    Semantic search over stored vectors.
    Generates query embedding via NVIDIA NIM, then cosine similarity search.
    
    Input: Natural language query
    Output: Top-K most similar chunks with scores
    """
    cache_key = f"search:{data.namespace}:{data.query[:100]}"
    cached = search_cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    # Generate query embedding
    try:
        query_embedding = await nvidia_client.generate_embedding(data.query)
    except Exception as e:
        logger.warning(f"Query embedding failed: {e}; using fallback")
        import hashlib
        h = hashlib.sha512(data.query.encode()).digest()
        query_embedding = [(h[i % len(h)] / 127.5) - 1.0 for i in range(EMBEDDING_DIM)]

    results = vector_index.search(
        query_embedding, top_k=data.top_k,
        namespace=data.namespace, min_score=data.min_score,
    )

    search_results = [{
        "vector_id": vec_id,
        "score": round(score, 4),
        "content": meta.get("content", ""),
        "policy_id": meta.get("policy_id"),
        "document_id": meta.get("document_id"),
        "chunk_id": meta.get("chunk_id"),
    } for vec_id, score, meta in results]

    result = {"query": data.query, "results": search_results, "total": len(search_results)}
    search_cache.set(cache_key, result)
    return ApiResponse(data=result)


@app.post("/vectors/search/embedding", response_model=ApiResponse, tags=["Search"])
async def search_by_embedding(data: SearchByEmbeddingRequest):
    """Search using a pre-computed embedding vector."""
    results = vector_index.search(
        data.embedding, top_k=data.top_k,
        namespace=data.namespace, min_score=data.min_score,
    )
    return ApiResponse(data={
        "results": [{
            "vector_id": vid, "score": round(s, 4),
            "content": m.get("content", ""),
            "policy_id": m.get("policy_id"),
        } for vid, s, m in results],
    })


@app.delete("/vectors/{vector_id}", response_model=ApiResponse, tags=["Vectors"])
async def delete_vector(vector_id: str):
    """Remove a vector from the index and database."""
    async with AsyncSessionLocal() as session:
        await session.execute(delete(VectorRecord).where(VectorRecord.id == vector_id))
        await session.commit()
    vector_index.remove(vector_id)
    return ApiResponse(message="Vector deleted")


@app.delete("/vectors/document/{document_id}", response_model=ApiResponse, tags=["Vectors"])
async def delete_by_document(document_id: str):
    """Remove all vectors for a document."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(VectorRecord.id).where(VectorRecord.document_id == document_id)
        )).scalars().all()
        for vid in rows:
            vector_index.remove(vid)
        await session.execute(delete(VectorRecord).where(VectorRecord.document_id == document_id))
        await session.commit()
    return ApiResponse(message=f"Deleted {len(rows)} vectors")


@app.get("/vectors/stats", response_model=ApiResponse, tags=["Stats"])
async def vector_stats():
    """Get vector database statistics."""
    async with AsyncSessionLocal() as session:
        total = (await session.execute(select(func.count(VectorRecord.id)))).scalar() or 0
        namespaces = (await session.execute(
            select(VectorRecord.namespace, func.count(VectorRecord.id)).group_by(VectorRecord.namespace)
        )).all()

    return ApiResponse(data={
        "total_vectors": total,
        "index_size": vector_index.size,
        "embedding_dim": EMBEDDING_DIM,
        "namespaces": {ns: cnt for ns, cnt in namespaces},
    })
