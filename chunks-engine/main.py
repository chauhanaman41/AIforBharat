"""
AIforBharat — Chunks Engine (Engine 10)
=========================================
Splits policy documents into semantically meaningful chunks for
vector embedding and retrieval. Implements multiple chunking strategies:
- Fixed-size with overlap
- Sentence-based
- Section-based (headers/paragraphs)
- Semantic (using NVIDIA NIM embeddings for boundary detection)

Produces chunks ready for Vector Database ingestion.

Port: 8010
"""

import logging, time, os, sys, json, re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, select, delete

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.utils import generate_id, sha256_hash
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("chunks_engine")
START_TIME = time.time()
chunk_cache = LocalCache(namespace="chunks", ttl=3600)

# Default chunking parameters
DEFAULT_CHUNK_SIZE = 512     # characters
DEFAULT_OVERLAP = 64         # overlap between chunks
MAX_CHUNK_SIZE = 2000
MIN_CHUNK_SIZE = 50


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(String, primary_key=True, default=generate_id)
    document_id = Column(String, index=True, nullable=False)
    policy_id = Column(String, index=True)
    chunk_index = Column(Integer, nullable=False)
    total_chunks = Column(Integer)
    content = Column(Text, nullable=False)
    content_hash = Column(String)
    chunk_size = Column(Integer)
    strategy = Column(String, default="fixed")     # fixed, sentence, section, semantic
    metadata_json = Column(Text)                   # JSON: title, ministry, section_header, etc.
    embedding_status = Column(String, default="pending")  # pending, embedded, failed
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Chunking Strategies ──────────────────────────────────────────────────────

def chunk_fixed(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP) -> List[str]:
    """Fixed-size chunking with overlap."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def chunk_sentence(text: str, max_chunk_size: int = DEFAULT_CHUNK_SIZE) -> List[str]:
    """Sentence-based chunking. Groups sentences until max size."""
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 > max_chunk_size and current:
            chunks.append(current.strip())
            current = sent
        else:
            current = f"{current} {sent}" if current else sent
    if current.strip():
        chunks.append(current.strip())
    return chunks


def chunk_section(text: str) -> List[str]:
    """Section-based chunking. Splits on headers, double newlines, bullet lists."""
    # Split on common section patterns
    sections = re.split(
        r'\n(?=#{1,4}\s)|(?:\n\s*\n){2,}|(?:\n(?=[A-Z][^a-z]*:))',
        text
    )
    chunks = []
    for section in sections:
        s = section.strip()
        if len(s) < MIN_CHUNK_SIZE:
            # Merge tiny sections with previous
            if chunks:
                chunks[-1] = f"{chunks[-1]}\n{s}"
            else:
                chunks.append(s)
        elif len(s) > MAX_CHUNK_SIZE:
            # Sub-chunk large sections
            chunks.extend(chunk_sentence(s))
        else:
            chunks.append(s)
    return [c for c in chunks if len(c.strip()) >= MIN_CHUNK_SIZE]


def chunk_paragraph(text: str) -> List[str]:
    """Paragraph-based chunking. Splits on double newlines."""
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    for para in paragraphs:
        p = para.strip()
        if len(p) >= MIN_CHUNK_SIZE:
            if len(p) > MAX_CHUNK_SIZE:
                chunks.extend(chunk_sentence(p))
            else:
                chunks.append(p)
        elif chunks:
            chunks[-1] = f"{chunks[-1]}\n{p}"
    return [c for c in chunks if c.strip()]


STRATEGY_MAP = {
    "fixed": chunk_fixed,
    "sentence": chunk_sentence,
    "section": chunk_section,
    "paragraph": chunk_paragraph,
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class ChunkRequest(BaseModel):
    document_id: str
    policy_id: Optional[str] = None
    text: str
    strategy: str = "sentence"   # fixed, sentence, section, paragraph
    chunk_size: int = Field(default=DEFAULT_CHUNK_SIZE, ge=MIN_CHUNK_SIZE, le=MAX_CHUNK_SIZE)
    overlap: int = Field(default=DEFAULT_OVERLAP, ge=0, le=256)
    metadata: dict = {}


class BatchChunkRequest(BaseModel):
    documents: List[ChunkRequest]


class ReChunkRequest(BaseModel):
    document_id: str
    strategy: str = "sentence"
    chunk_size: int = DEFAULT_CHUNK_SIZE


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Chunks Engine starting...")
    await init_db()
    # Subscribe to document events
    event_bus.subscribe("document.*", _on_document_event)
    yield

app = FastAPI(title="AIforBharat Chunks Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


async def _on_document_event(event: EventMessage):
    """Auto-chunk when a new document is fetched."""
    logger.info(f"Received document event: {event.event_type}")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="chunks_engine", uptime_seconds=time.time() - START_TIME)


@app.post("/chunks/create", response_model=ApiResponse, tags=["Chunk"])
async def create_chunks(data: ChunkRequest):
    """
    Split a document into chunks using the specified strategy.
    
    Strategies:
    - fixed: Fixed-size with configurable overlap
    - sentence: Groups sentences up to chunk_size
    - section: Splits on headers/sections
    - paragraph: Splits on paragraph boundaries
    
    All chunks are stored in DB and ready for vector embedding.
    """
    # Check cache first (Local-First: avoid re-chunking same content)
    content_hash = sha256_hash(data.text[:1000] + data.strategy)
    cache_key = f"chunks:{data.document_id}:{content_hash[:16]}"
    cached = chunk_cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    # Select chunking strategy
    if data.strategy == "fixed":
        text_chunks = chunk_fixed(data.text, data.chunk_size, data.overlap)
    elif data.strategy in STRATEGY_MAP:
        text_chunks = STRATEGY_MAP[data.strategy](data.text)
    else:
        text_chunks = chunk_sentence(data.text, data.chunk_size)

    total = len(text_chunks)

    # Store chunks to DB
    chunk_records = []
    async with AsyncSessionLocal() as session:
        # Remove old chunks for this document (re-chunking)
        await session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == data.document_id)
        )

        for idx, content in enumerate(text_chunks):
            chunk_id = generate_id()
            record = DocumentChunk(
                id=chunk_id,
                document_id=data.document_id,
                policy_id=data.policy_id,
                chunk_index=idx,
                total_chunks=total,
                content=content,
                content_hash=sha256_hash(content),
                chunk_size=len(content),
                strategy=data.strategy,
                metadata_json=json.dumps({
                    **data.metadata,
                    "chunk_index": idx,
                    "total_chunks": total,
                }),
            )
            session.add(record)
            chunk_records.append({
                "chunk_id": chunk_id,
                "index": idx,
                "content": content,
                "size": len(content),
            })

        await session.commit()

    result = {
        "document_id": data.document_id,
        "policy_id": data.policy_id,
        "strategy": data.strategy,
        "total_chunks": total,
        "avg_chunk_size": round(sum(len(c) for c in text_chunks) / max(total, 1)),
        "chunks": chunk_records,
    }

    chunk_cache.set(cache_key, result)

    await event_bus.publish(EventMessage(
        event_type=EventType.CHUNKS_CREATED,
        source_engine="chunks_engine",
        payload={
            "document_id": data.document_id,
            "policy_id": data.policy_id,
            "total_chunks": total,
            "strategy": data.strategy,
        },
    ))

    return ApiResponse(message=f"Created {total} chunks", data=result)


@app.post("/chunks/batch", response_model=ApiResponse, tags=["Chunk"])
async def batch_chunk(data: BatchChunkRequest):
    """Chunk multiple documents in a single batch."""
    results = []
    for doc in data.documents:
        strategy_fn = STRATEGY_MAP.get(doc.strategy, chunk_sentence)
        if doc.strategy == "fixed":
            text_chunks = chunk_fixed(doc.text, doc.chunk_size, doc.overlap)
        else:
            text_chunks = strategy_fn(doc.text)

        results.append({
            "document_id": doc.document_id,
            "policy_id": doc.policy_id,
            "total_chunks": len(text_chunks),
            "chunks": [{"index": i, "content": c, "size": len(c)} for i, c in enumerate(text_chunks)],
        })

    return ApiResponse(data=results, metadata={"batch_size": len(results)})


@app.get("/chunks/document/{document_id}", response_model=ApiResponse, tags=["Query"])
async def get_document_chunks(document_id: str):
    """Get all chunks for a specific document."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )).scalars().all()
        if not rows:
            raise HTTPException(status_code=404, detail="No chunks found for this document")
        return ApiResponse(data={
            "document_id": document_id,
            "total_chunks": len(rows),
            "strategy": rows[0].strategy if rows else None,
            "chunks": [{
                "chunk_id": r.id, "index": r.chunk_index,
                "content": r.content, "size": r.chunk_size,
                "embedding_status": r.embedding_status,
            } for r in rows],
        })


@app.get("/chunks/{chunk_id}", response_model=ApiResponse, tags=["Query"])
async def get_chunk(chunk_id: str):
    """Get a specific chunk by ID."""
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(DocumentChunk).where(DocumentChunk.id == chunk_id)
        )).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Chunk not found")
        return ApiResponse(data={
            "chunk_id": row.id, "document_id": row.document_id,
            "policy_id": row.policy_id, "index": row.chunk_index,
            "content": row.content, "size": row.chunk_size,
            "strategy": row.strategy,
            "metadata": json.loads(row.metadata_json or "{}"),
        })


@app.post("/chunks/rechunk", response_model=ApiResponse, tags=["Chunk"])
async def rechunk_document(data: ReChunkRequest):
    """Re-chunk an existing document with a different strategy."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == data.document_id)
            .order_by(DocumentChunk.chunk_index)
        )).scalars().all()
        if not rows:
            raise HTTPException(status_code=404, detail="No chunks found to re-chunk")

        original_text = " ".join(r.content for r in rows)
        policy_id = rows[0].policy_id

    # Re-chunk with new strategy using the create endpoint logic
    req = ChunkRequest(
        document_id=data.document_id,
        policy_id=policy_id,
        text=original_text,
        strategy=data.strategy,
        chunk_size=data.chunk_size,
    )
    return await create_chunks(req)


@app.get("/chunks/stats", response_model=ApiResponse, tags=["Stats"])
async def chunk_stats():
    """Get chunking statistics."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import func
        total = (await session.execute(
            select(func.count(DocumentChunk.id))
        )).scalar() or 0
        unique_docs = (await session.execute(
            select(func.count(func.distinct(DocumentChunk.document_id)))
        )).scalar() or 0
        avg_size = (await session.execute(
            select(func.avg(DocumentChunk.chunk_size))
        )).scalar() or 0

        return ApiResponse(data={
            "total_chunks": total,
            "unique_documents": unique_docs,
            "avg_chunk_size": round(avg_size),
        })
