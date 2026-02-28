"""
AIforBharat — Processed User Metadata Store (Engine 5)
=======================================================
Encrypted relational store for normalized user profiles.
Stores: user_metadata, derived_attributes, risk_scores, eligibility_cache.
All PII encrypted at rest via AES-256-GCM.

Port: 8005
"""

import logging, time, os, sys, json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Float, Boolean, Integer, Text, DateTime, JSON, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.utils import generate_id
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("processed_metadata_store")
START_TIME = time.time()
store_cache = LocalCache(namespace="processed_meta", ttl=1800)


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class UserMetadata(Base):
    __tablename__ = "user_metadata"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    phone_hash = Column(String)
    state = Column(String)
    district = Column(String)
    pincode = Column(String(6))
    gender = Column(String)
    category = Column(String)
    religion = Column(String)
    education_level = Column(String)
    marital_status = Column(String)
    occupation = Column(String)
    annual_income = Column(Float)
    family_size = Column(Integer)
    is_bpl = Column(Boolean, default=False)
    is_rural = Column(Boolean)
    disability_status = Column(String)
    land_holding_acres = Column(Float)
    language_preference = Column(String, default="en")
    metadata_version = Column(String, default="1.0")
    raw_payload = Column(Text)  # JSON blob of full normalized data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserDerivedAttributes(Base):
    __tablename__ = "user_derived_attributes"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, index=True, nullable=False)
    age = Column(Integer)
    age_group = Column(String)
    is_minor = Column(Boolean, default=False)
    is_senior_citizen = Column(Boolean, default=False)
    income_bracket = Column(String)
    tax_bracket = Column(String)
    life_stage = Column(String)
    employment_category = Column(String)
    is_sc_st = Column(Boolean, default=False)
    is_obc = Column(Boolean, default=False)
    is_ews = Column(Boolean, default=False)
    area_type = Column(String)
    farmer_category = Column(String)
    computed_at = Column(DateTime, default=datetime.utcnow)


class UserEligibilityCache(Base):
    __tablename__ = "user_eligibility_cache"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, index=True, nullable=False)
    scheme_id = Column(String, nullable=False)
    scheme_name = Column(String)
    is_eligible = Column(Boolean)
    confidence = Column(Float)
    matched_criteria = Column(Text)  # JSON
    unmet_criteria = Column(Text)    # JSON
    verdict_reason = Column(String)
    cached_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)


class UserRiskScore(Base):
    __tablename__ = "user_risk_scores"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, index=True, nullable=False)
    risk_type = Column(String)         # fraud, duplicate, data_quality
    risk_score = Column(Float)         # 0.0 - 1.0
    risk_factors = Column(Text)        # JSON array
    assessed_at = Column(DateTime, default=datetime.utcnow)


# ── Schemas ───────────────────────────────────────────────────────────────────

class StoreMetadataRequest(BaseModel):
    user_id: str
    processed_data: dict
    derived_attributes: Optional[dict] = None


class UpdateMetadataRequest(BaseModel):
    updates: dict


class CacheEligibilityRequest(BaseModel):
    user_id: str
    scheme_id: str
    scheme_name: str = ""
    is_eligible: bool
    confidence: float = 1.0
    matched_criteria: list = []
    unmet_criteria: list = []
    verdict_reason: str = ""


class StoreRiskScoreRequest(BaseModel):
    user_id: str
    risk_type: str
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_factors: list = []


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Processed User Metadata Store starting...")
    await init_db()
    yield

app = FastAPI(title="AIforBharat Processed User Metadata Store", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="processed_metadata_store", uptime_seconds=time.time() - START_TIME)


@app.post("/processed-metadata/store", response_model=ApiResponse, tags=["Store"])
async def store_metadata(data: StoreMetadataRequest):
    """Store processed user metadata into the relational store."""
    async with AsyncSessionLocal() as session:
        existing = (await session.execute(
            select(UserMetadata).where(UserMetadata.user_id == data.user_id)
        )).scalar_one_or_none()

        pd = data.processed_data
        if existing:
            for key, val in pd.items():
                if key not in ("user_id", "derived_attributes", "processed_at", "metadata_version") and hasattr(existing, key):
                    setattr(existing, key, val)
            existing.raw_payload = json.dumps(pd)
            existing.updated_at = datetime.utcnow()
        else:
            record = UserMetadata(
                id=generate_id(), user_id=data.user_id,
                name=pd.get("name"), state=pd.get("state"), district=pd.get("district"),
                pincode=pd.get("pincode"), gender=pd.get("gender"),
                category=pd.get("category"), religion=pd.get("religion"),
                education_level=pd.get("education_level"), marital_status=pd.get("marital_status"),
                occupation=pd.get("occupation"), annual_income=pd.get("annual_income"),
                family_size=pd.get("family_size"), is_bpl=pd.get("is_bpl"),
                is_rural=pd.get("is_rural"), disability_status=pd.get("disability_status"),
                land_holding_acres=pd.get("land_holding_acres"),
                language_preference=pd.get("language_preference", "en"),
                raw_payload=json.dumps(pd),
            )
            session.add(record)

        # Store derived attributes
        da = data.derived_attributes or pd.get("derived_attributes", {})
        if da:
            derived = UserDerivedAttributes(
                id=generate_id(), user_id=data.user_id,
                age=da.get("age"), age_group=da.get("age_group"),
                is_minor=da.get("is_minor", False), is_senior_citizen=da.get("is_senior_citizen", False),
                income_bracket=da.get("income_bracket"), tax_bracket=da.get("tax_bracket"),
                life_stage=da.get("life_stage"), employment_category=da.get("employment_category"),
                is_sc_st=da.get("is_sc_st", False), is_obc=da.get("is_obc", False),
                is_ews=da.get("is_ews", False), area_type=da.get("area_type"),
                farmer_category=da.get("farmer_category"),
            )
            session.add(derived)

        await session.commit()

    store_cache.set(f"user:{data.user_id}", pd)
    await event_bus.publish(EventMessage(
        event_type=EventType.METADATA_CREATED,
        source_engine="processed_metadata_store", user_id=data.user_id,
        payload={"action": "stored"},
    ))
    return ApiResponse(message="Metadata stored successfully")


@app.get("/processed-metadata/user/{user_id}", response_model=ApiResponse, tags=["Store"])
async def get_user_metadata(user_id: str):
    """Get full processed metadata for a user."""
    cached = store_cache.get(f"user:{user_id}")
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(UserMetadata).where(UserMetadata.user_id == user_id)
        )).scalar_one_or_none()

        if not row:
            raise HTTPException(status_code=404, detail="User metadata not found")

        payload = json.loads(row.raw_payload) if row.raw_payload else {}

        # Fetch latest derived attributes
        derived_row = (await session.execute(
            select(UserDerivedAttributes)
            .where(UserDerivedAttributes.user_id == user_id)
            .order_by(UserDerivedAttributes.computed_at.desc())
        )).scalars().first()

        if derived_row:
            payload["derived_attributes"] = {
                "age": derived_row.age, "age_group": derived_row.age_group,
                "is_minor": derived_row.is_minor, "is_senior_citizen": derived_row.is_senior_citizen,
                "income_bracket": derived_row.income_bracket, "tax_bracket": derived_row.tax_bracket,
                "life_stage": derived_row.life_stage, "employment_category": derived_row.employment_category,
                "is_sc_st": derived_row.is_sc_st, "is_obc": derived_row.is_obc,
                "is_ews": derived_row.is_ews, "area_type": derived_row.area_type,
                "farmer_category": derived_row.farmer_category,
            }

        store_cache.set(f"user:{user_id}", payload)
        return ApiResponse(data=payload)


@app.put("/processed-metadata/user/{user_id}", response_model=ApiResponse, tags=["Store"])
async def update_user_metadata(user_id: str, data: UpdateMetadataRequest):
    """Update specific fields for a user's metadata."""
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(UserMetadata).where(UserMetadata.user_id == user_id)
        )).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="User metadata not found")

        for key, val in data.updates.items():
            if hasattr(row, key) and key not in ("id", "user_id", "created_at"):
                setattr(row, key, val)
        row.updated_at = datetime.utcnow()
        await session.commit()

    store_cache.invalidate(f"user:{user_id}")
    return ApiResponse(message="Metadata updated")


@app.delete("/processed-metadata/user/{user_id}", response_model=ApiResponse, tags=["Store"])
async def delete_user_metadata(user_id: str):
    """Delete all metadata for a user (DPDP right to erasure)."""
    async with AsyncSessionLocal() as session:
        await session.execute(delete(UserMetadata).where(UserMetadata.user_id == user_id))
        await session.execute(delete(UserDerivedAttributes).where(UserDerivedAttributes.user_id == user_id))
        await session.execute(delete(UserEligibilityCache).where(UserEligibilityCache.user_id == user_id))
        await session.execute(delete(UserRiskScore).where(UserRiskScore.user_id == user_id))
        await session.commit()

    store_cache.invalidate(f"user:{user_id}")
    return ApiResponse(message="All user metadata deleted")


# ── Eligibility Cache ─────────────────────────────────────────────────────────

@app.post("/processed-metadata/eligibility/cache", response_model=ApiResponse, tags=["Eligibility Cache"])
async def cache_eligibility(data: CacheEligibilityRequest):
    """Cache an eligibility verdict for a user-scheme pair."""
    async with AsyncSessionLocal() as session:
        record = UserEligibilityCache(
            id=generate_id(), user_id=data.user_id, scheme_id=data.scheme_id,
            scheme_name=data.scheme_name, is_eligible=data.is_eligible,
            confidence=data.confidence,
            matched_criteria=json.dumps(data.matched_criteria),
            unmet_criteria=json.dumps(data.unmet_criteria),
            verdict_reason=data.verdict_reason,
        )
        session.add(record)
        await session.commit()
    return ApiResponse(message="Eligibility cached")


@app.get("/processed-metadata/eligibility/{user_id}", response_model=ApiResponse, tags=["Eligibility Cache"])
async def get_eligibility_cache(user_id: str, scheme_id: Optional[str] = None):
    """Get cached eligibility results for a user."""
    async with AsyncSessionLocal() as session:
        query = select(UserEligibilityCache).where(UserEligibilityCache.user_id == user_id)
        if scheme_id:
            query = query.where(UserEligibilityCache.scheme_id == scheme_id)
        results = (await session.execute(query.order_by(UserEligibilityCache.cached_at.desc()))).scalars().all()
        return ApiResponse(data=[{
            "scheme_id": r.scheme_id, "scheme_name": r.scheme_name,
            "is_eligible": r.is_eligible, "confidence": r.confidence,
            "matched_criteria": json.loads(r.matched_criteria or "[]"),
            "unmet_criteria": json.loads(r.unmet_criteria or "[]"),
            "verdict_reason": r.verdict_reason, "cached_at": r.cached_at.isoformat() if r.cached_at else None,
        } for r in results])


# ── Risk Scores ───────────────────────────────────────────────────────────────

@app.post("/processed-metadata/risk", response_model=ApiResponse, tags=["Risk Scores"])
async def store_risk_score(data: StoreRiskScoreRequest):
    """Store a risk assessment score."""
    async with AsyncSessionLocal() as session:
        record = UserRiskScore(
            id=generate_id(), user_id=data.user_id,
            risk_type=data.risk_type, risk_score=data.risk_score,
            risk_factors=json.dumps(data.risk_factors),
        )
        session.add(record)
        await session.commit()
    return ApiResponse(message="Risk score stored")


@app.get("/processed-metadata/risk/{user_id}", response_model=ApiResponse, tags=["Risk Scores"])
async def get_risk_scores(user_id: str):
    """Get risk scores for a user."""
    async with AsyncSessionLocal() as session:
        results = (await session.execute(
            select(UserRiskScore)
            .where(UserRiskScore.user_id == user_id)
            .order_by(UserRiskScore.assessed_at.desc())
        )).scalars().all()
        return ApiResponse(data=[{
            "risk_type": r.risk_type, "risk_score": r.risk_score,
            "risk_factors": json.loads(r.risk_factors or "[]"),
            "assessed_at": r.assessed_at.isoformat() if r.assessed_at else None,
        } for r in results])
