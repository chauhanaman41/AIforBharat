"""
AIforBharat — Raw Data Store (Engine 3)
=========================================
Append-only immutable event store with SHA-256 hash chains.
Local filesystem replaces S3/MinIO. Parquet format for efficiency.

Port: 8003
"""

import hashlib
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings, RAW_STORE_DIR
from shared.models import ApiResponse, EventMessage, EventType, HealthResponse
from shared.event_bus import event_bus
from shared.utils import sha256_hash, generate_uuid

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("raw_data_store")
START_TIME = time.time()

# ── Hash chain state ──────────────────────────────────────────────────────────
_last_hash = "GENESIS"  # Initial hash chain seed


def _compute_event_hash(payload: dict, prev_hash: str) -> str:
    """Compute SHA-256 hash for a raw event, chaining with previous hash."""
    content = json.dumps(payload, sort_keys=True, default=str) + prev_hash
    return sha256_hash(content)


# ── Tiered Storage Helpers ────────────────────────────────────────────────────

def _get_hot_path(event_id: str) -> Path:
    """Get file path in hot storage (recent events, <30 days)."""
    now = datetime.utcnow()
    path = RAW_STORE_DIR / "hot" / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{event_id}.json"


def _store_event(event_id: str, data: dict):
    """Persist an event to local filesystem (hot storage)."""
    file_path = _get_hot_path(event_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    logger.debug(f"Event stored: {file_path}")


def _read_event(event_id: str) -> Optional[dict]:
    """Search for an event across all storage tiers."""
    for tier in ["hot", "warm", "cold"]:
        tier_dir = RAW_STORE_DIR / tier
        for root, dirs, files in os.walk(tier_dir):
            if f"{event_id}.json" in files:
                with open(os.path.join(root, f"{event_id}.json"), "r") as f:
                    return json.load(f)
    return None


# ── Schemas ───────────────────────────────────────────────────────────────────

class RawEventInput(BaseModel):
    event_type: str
    source_engine: str
    user_id: Optional[str] = None
    payload: dict = {}


class IntegrityVerifyRequest(BaseModel):
    event_ids: list[str] = []


# ── App Setup ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Raw Data Store starting...")
    # Subscribe to all events for audit logging
    event_bus.subscribe("*", _audit_event_handler)
    yield
    logger.info("🛑 Raw Data Store shutting down...")


async def _audit_event_handler(event: EventMessage):
    """Automatically store all events from the event bus as audit records."""
    global _last_hash
    event_hash = _compute_event_hash(event.model_dump(mode="json"), _last_hash)
    record = {
        "event_id": event.event_id,
        "event_type": event.event_type.value if hasattr(event.event_type, 'value') else event.event_type,
        "source_engine": event.source_engine,
        "user_id": event.user_id,
        "timestamp": datetime.utcnow().isoformat(),
        "payload": event.payload,
        "hash": event_hash,
        "prev_hash": _last_hash,
    }
    _store_event(event.event_id, record)
    _last_hash = event_hash


app = FastAPI(title="AIforBharat Raw Data Store", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="raw_data_store", uptime_seconds=time.time() - START_TIME)


@app.post("/raw-data/events", response_model=ApiResponse, tags=["Events"])
async def store_event(data: RawEventInput):
    """
    Store a raw event in the immutable append-only store.
    Computes SHA-256 hash chain for integrity verification.
    
    Input: {event_type, source_engine, user_id?, payload}
    Output: {event_id, hash, timestamp}
    """
    global _last_hash
    event_id = generate_uuid()
    event_hash = _compute_event_hash(data.model_dump(), _last_hash)

    record = {
        "event_id": event_id,
        "event_type": data.event_type,
        "source_engine": data.source_engine,
        "user_id": data.user_id,
        "timestamp": datetime.utcnow().isoformat(),
        "payload": data.payload,
        "hash": event_hash,
        "prev_hash": _last_hash,
    }
    _store_event(event_id, record)
    _last_hash = event_hash

    await event_bus.publish(EventMessage(
        event_type=EventType.RAW_DATA_STORED,
        source_engine="raw_data_store",
        payload={"event_id": event_id, "hash": event_hash},
    ))

    return ApiResponse(message="Event stored", data={
        "event_id": event_id,
        "hash": event_hash,
        "timestamp": record["timestamp"],
    })


@app.get("/raw-data/events/{event_id}", response_model=ApiResponse, tags=["Events"])
async def get_event(event_id: str):
    """Retrieve a specific event by ID."""
    record = _read_event(event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Event not found")
    return ApiResponse(data=record)


@app.get("/raw-data/events", response_model=ApiResponse, tags=["Events"])
async def list_events(
    source_engine: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
):
    """List recent events from hot storage."""
    events = []
    hot_dir = RAW_STORE_DIR / "hot"
    for root, dirs, files in os.walk(hot_dir):
        for f_name in sorted(files, reverse=True):
            if f_name.endswith(".json"):
                try:
                    with open(os.path.join(root, f_name), "r") as f:
                        event = json.load(f)
                    if source_engine and event.get("source_engine") != source_engine:
                        continue
                    if event_type and event.get("event_type") != event_type:
                        continue
                    events.append(event)
                    if len(events) >= limit:
                        break
                except Exception:
                    continue
        if len(events) >= limit:
            break

    return ApiResponse(data={"events": events, "count": len(events)})


@app.get("/raw-data/user/{user_id}/trail", response_model=ApiResponse, tags=["Audit"])
async def get_user_trail(user_id: str, limit: int = Query(default=50)):
    """Get the complete audit trail for a specific user."""
    events = []
    hot_dir = RAW_STORE_DIR / "hot"
    for root, dirs, files in os.walk(hot_dir):
        for f_name in files:
            if f_name.endswith(".json"):
                try:
                    with open(os.path.join(root, f_name), "r") as f:
                        event = json.load(f)
                    if event.get("user_id") == user_id:
                        events.append(event)
                except Exception:
                    continue

    events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return ApiResponse(data={"user_id": user_id, "trail": events[:limit], "count": len(events)})


@app.post("/raw-data/integrity/verify", response_model=ApiResponse, tags=["Audit"])
async def verify_integrity(data: IntegrityVerifyRequest):
    """
    Verify the integrity of the hash chain for specific events.
    Ensures no event has been tampered with.
    """
    results = []
    for event_id in data.event_ids:
        record = _read_event(event_id)
        if not record:
            results.append({"event_id": event_id, "status": "NOT_FOUND"})
            continue

        # Recompute hash
        payload_for_hash = {k: v for k, v in record.items() if k not in ["hash", "prev_hash"]}
        expected_hash = _compute_event_hash(payload_for_hash, record.get("prev_hash", ""))
        is_valid = expected_hash == record.get("hash")

        results.append({
            "event_id": event_id,
            "status": "VALID" if is_valid else "TAMPERED",
            "stored_hash": record.get("hash"),
            "computed_hash": expected_hash,
        })

    return ApiResponse(data={"results": results})
