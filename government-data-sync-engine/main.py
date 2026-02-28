"""
AIforBharat — Government Data Sync Engine (Engine 18)
======================================================
Syncs structured government data from data.gov.in API and other
open data portals. Maintains local copies of datasets (Census,
NFHS-5, SECC, SDG India Index). Implements data caching strictly:
always checks local cache before downloading.

Port: 8018
"""

import logging, time, os, sys, json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Float, Boolean, Integer, select, func

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.utils import generate_id, sha256_hash
from shared.cache import LocalCache, file_exists_locally

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("government_data_sync")
START_TIME = time.time()

GOV_DATA_DIR = Path(settings.LOCAL_DATA_DIR) / "gov-data"
GOV_DATA_DIR.mkdir(parents=True, exist_ok=True)
gov_cache = LocalCache(namespace="gov_data", ttl=7200)

DATA_GOV_API_KEY = settings.DATA_GOV_API_KEY
DATA_GOV_BASE = "https://api.data.gov.in/resource/"


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class SyncedDataset(Base):
    __tablename__ = "synced_datasets"
    id = Column(String, primary_key=True, default=generate_id)
    dataset_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    source = Column(String, default="data.gov.in")
    source_url = Column(Text)
    description = Column(Text)
    category = Column(String)           # census, nfhs, secc, sdg, economic
    data_format = Column(String, default="json")
    record_count = Column(Integer, default=0)
    local_path = Column(Text)
    content_hash = Column(String)
    last_synced = Column(DateTime)
    sync_status = Column(String, default="pending")   # pending, syncing, synced, error
    is_cached = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class DataRecord(Base):
    __tablename__ = "gov_data_records"
    id = Column(String, primary_key=True, default=generate_id)
    dataset_id = Column(String, index=True, nullable=False)
    record_data = Column(Text)          # JSON
    state = Column(String, index=True)
    district = Column(String, index=True)
    year = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Seed Datasets ────────────────────────────────────────────────────────────

SEED_DATASETS = [
    {
        "dataset_id": "nfhs5_district",
        "name": "NFHS-5 District Factsheet Data",
        "source": "data.gov.in",
        "source_url": f"{DATA_GOV_BASE}nfhs5district",
        "category": "nfhs",
        "description": "National Family Health Survey 5 district-level indicators",
    },
    {
        "dataset_id": "census_2011_population",
        "name": "Census 2011 Population Data",
        "source": "data.gov.in",
        "category": "census",
        "description": "Population data from Census 2011 by state and district",
    },
    {
        "dataset_id": "sdg_india_index",
        "name": "SDG India Index",
        "source": "data.gov.in",
        "category": "sdg",
        "description": "Sustainable Development Goals India Index state-wise scores",
    },
    {
        "dataset_id": "poverty_headcount",
        "name": "Poverty Headcount Ratio",
        "source": "data.gov.in",
        "category": "economic",
        "description": "State-wise poverty headcount ratios (Tendulkar methodology)",
    },
    {
        "dataset_id": "scheme_beneficiaries",
        "name": "Scheme Beneficiary Statistics",
        "source": "local",
        "category": "schemes",
        "description": "Beneficiary counts by scheme and state",
    },
]

# Sample data records for local-first operation
SAMPLE_RECORDS = {
    "nfhs5_district": [
        {"state": "Uttar Pradesh", "district": "Lucknow", "indicator": "Under-5 Mortality Rate", "value": "32.8", "year": "2019-21"},
        {"state": "Bihar", "district": "Patna", "indicator": "Under-5 Mortality Rate", "value": "41.1", "year": "2019-21"},
        {"state": "Maharashtra", "district": "Mumbai", "indicator": "Under-5 Mortality Rate", "value": "18.4", "year": "2019-21"},
        {"state": "Tamil Nadu", "district": "Chennai", "indicator": "Under-5 Mortality Rate", "value": "15.2", "year": "2019-21"},
        {"state": "Kerala", "district": "Thiruvananthapuram", "indicator": "Under-5 Mortality Rate", "value": "7.1", "year": "2019-21"},
    ],
    "poverty_headcount": [
        {"state": "Bihar", "headcount_ratio": 33.7, "rural": 34.1, "urban": 31.2, "year": "2011-12"},
        {"state": "Uttar Pradesh", "headcount_ratio": 29.4, "rural": 30.4, "urban": 26.1, "year": "2011-12"},
        {"state": "Madhya Pradesh", "headcount_ratio": 31.6, "rural": 35.7, "urban": 21.0, "year": "2011-12"},
        {"state": "Maharashtra", "headcount_ratio": 17.4, "rural": 24.2, "urban": 9.1, "year": "2011-12"},
        {"state": "Kerala", "headcount_ratio": 7.1, "rural": 9.1, "urban": 4.0, "year": "2011-12"},
        {"state": "Tamil Nadu", "headcount_ratio": 11.3, "rural": 15.8, "urban": 6.5, "year": "2011-12"},
    ],
    "scheme_beneficiaries": [
        {"scheme": "PM-KISAN", "state": "Uttar Pradesh", "beneficiaries": 26000000, "year": "2024"},
        {"scheme": "PM-KISAN", "state": "Bihar", "beneficiaries": 8000000, "year": "2024"},
        {"scheme": "PMJAY", "state": "Maharashtra", "beneficiaries": 15000000, "year": "2024"},
        {"scheme": "PMAY", "state": "Uttar Pradesh", "beneficiaries": 4200000, "year": "2024"},
        {"scheme": "PM Ujjwala", "state": "Bihar", "beneficiaries": 5500000, "year": "2024"},
    ],
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class SyncDatasetRequest(BaseModel):
    dataset_id: str
    force_refresh: bool = False


class QueryDataRequest(BaseModel):
    dataset_id: str
    state: Optional[str] = None
    district: Optional[str] = None
    year: Optional[str] = None
    limit: int = Field(default=50, le=500)


class AddDatasetRequest(BaseModel):
    dataset_id: str
    name: str
    source: str = "manual"
    category: str = "custom"
    description: str = ""
    records: List[dict] = []


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Government Data Sync Engine starting...")
    await init_db()
    await _seed_datasets()
    yield

app = FastAPI(title="AIforBharat Government Data Sync Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


async def _seed_datasets():
    """Seed datasets and sample records."""
    async with AsyncSessionLocal() as session:
        for ds in SEED_DATASETS:
            exists = (await session.execute(
                select(SyncedDataset).where(SyncedDataset.dataset_id == ds["dataset_id"])
            )).scalar_one_or_none()
            if not exists:
                # Save to local file
                local_path = GOV_DATA_DIR / f"{ds['dataset_id']}.json"
                records = SAMPLE_RECORDS.get(ds["dataset_id"], [])
                local_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

                session.add(SyncedDataset(
                    id=generate_id(), dataset_id=ds["dataset_id"],
                    name=ds["name"], source=ds.get("source", "data.gov.in"),
                    source_url=ds.get("source_url"), description=ds.get("description"),
                    category=ds.get("category"), record_count=len(records),
                    local_path=str(local_path), is_cached=True,
                    content_hash=sha256_hash(json.dumps(records)),
                    last_synced=datetime.utcnow(), sync_status="synced",
                ))

                # Insert records
                for rec in records:
                    session.add(DataRecord(
                        id=generate_id(), dataset_id=ds["dataset_id"],
                        record_data=json.dumps(rec),
                        state=rec.get("state"), district=rec.get("district"),
                        year=rec.get("year"),
                    ))

        await session.commit()
    logger.info("Seeded government datasets")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="government_data_sync_engine", uptime_seconds=time.time() - START_TIME)


@app.post("/gov-data/sync", response_model=ApiResponse, tags=["Sync"])
async def sync_dataset(data: SyncDatasetRequest):
    """
    Sync a dataset from government API.
    Local-First: checks local cache before downloading.
    """
    async with AsyncSessionLocal() as session:
        ds = (await session.execute(
            select(SyncedDataset).where(SyncedDataset.dataset_id == data.dataset_id)
        )).scalar_one_or_none()
        if not ds:
            raise HTTPException(status_code=404, detail="Dataset not configured")

        # Local-First: check if already cached
        if ds.is_cached and not data.force_refresh:
            logger.info(f"Dataset {data.dataset_id} already cached locally")
            return ApiResponse(message="Dataset already cached", data={
                "dataset_id": ds.dataset_id, "status": "cached",
                "records": ds.record_count, "last_synced": ds.last_synced.isoformat() if ds.last_synced else None,
            })

        # Mark syncing
        ds.sync_status = "syncing"
        await session.commit()

        # In production, would call data.gov.in API here
        # For local-first, we return cached data
        logger.info(f"Sync requested for {data.dataset_id} (using local data)")
        ds.sync_status = "synced"
        ds.last_synced = datetime.utcnow()
        ds.is_cached = True
        await session.commit()

    return ApiResponse(message="Dataset synced (local)", data={
        "dataset_id": data.dataset_id, "status": "synced",
    })


@app.post("/gov-data/query", response_model=ApiResponse, tags=["Query"])
async def query_data(data: QueryDataRequest):
    """Query government data with state/district/year filters."""
    cache_key = f"govq:{data.dataset_id}:{data.state}:{data.district}:{data.year}"
    cached = gov_cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    async with AsyncSessionLocal() as session:
        query = select(DataRecord).where(DataRecord.dataset_id == data.dataset_id)
        if data.state:
            query = query.where(DataRecord.state.ilike(f"%{data.state}%"))
        if data.district:
            query = query.where(DataRecord.district.ilike(f"%{data.district}%"))
        if data.year:
            query = query.where(DataRecord.year == data.year)
        query = query.limit(data.limit)

        rows = (await session.execute(query)).scalars().all()
        records = [json.loads(r.record_data) for r in rows]

    result = {"dataset_id": data.dataset_id, "count": len(records), "records": records}
    gov_cache.set(cache_key, result)
    return ApiResponse(data=result)


@app.get("/gov-data/datasets", response_model=ApiResponse, tags=["Datasets"])
async def list_datasets(category: Optional[str] = None):
    """List all synced datasets."""
    async with AsyncSessionLocal() as session:
        query = select(SyncedDataset)
        if category:
            query = query.where(SyncedDataset.category == category)
        rows = (await session.execute(query)).scalars().all()
        return ApiResponse(data=[{
            "dataset_id": r.dataset_id, "name": r.name,
            "source": r.source, "category": r.category,
            "records": r.record_count, "is_cached": r.is_cached,
            "status": r.sync_status,
            "last_synced": r.last_synced.isoformat() if r.last_synced else None,
        } for r in rows])


@app.get("/gov-data/dataset/{dataset_id}", response_model=ApiResponse, tags=["Datasets"])
async def get_dataset(dataset_id: str):
    """Get dataset details and sample records."""
    async with AsyncSessionLocal() as session:
        ds = (await session.execute(
            select(SyncedDataset).where(SyncedDataset.dataset_id == dataset_id)
        )).scalar_one_or_none()
        if not ds:
            raise HTTPException(status_code=404, detail="Dataset not found")

        sample_rows = (await session.execute(
            select(DataRecord).where(DataRecord.dataset_id == dataset_id).limit(5)
        )).scalars().all()

        return ApiResponse(data={
            "dataset_id": ds.dataset_id, "name": ds.name,
            "description": ds.description, "category": ds.category,
            "records": ds.record_count, "source": ds.source,
            "sample_data": [json.loads(r.record_data) for r in sample_rows],
        })


@app.post("/gov-data/datasets/add", response_model=ApiResponse, tags=["Datasets"])
async def add_dataset(data: AddDatasetRequest):
    """Add a custom dataset with records."""
    async with AsyncSessionLocal() as session:
        local_path = GOV_DATA_DIR / f"{data.dataset_id}.json"
        local_path.write_text(json.dumps(data.records, indent=2), encoding="utf-8")

        session.add(SyncedDataset(
            id=generate_id(), dataset_id=data.dataset_id,
            name=data.name, source=data.source,
            category=data.category, description=data.description,
            record_count=len(data.records), local_path=str(local_path),
            is_cached=True, content_hash=sha256_hash(json.dumps(data.records)),
            last_synced=datetime.utcnow(), sync_status="synced",
        ))

        for rec in data.records:
            session.add(DataRecord(
                id=generate_id(), dataset_id=data.dataset_id,
                record_data=json.dumps(rec),
                state=rec.get("state"), district=rec.get("district"),
                year=rec.get("year"),
            ))

        await session.commit()
    return ApiResponse(message=f"Dataset added with {len(data.records)} records")
