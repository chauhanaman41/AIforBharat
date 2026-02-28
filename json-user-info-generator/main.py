"""
AIforBharat — JSON User Info Generator (Engine 12)
====================================================
Assembles a comprehensive JSON profile for downstream engines by
aggregating data from: Metadata, Identity, Processed Metadata,
Eligibility, Trust Score, Anomaly Detection, and Deadline engines.
Single source of truth for user context in AI queries.

Port: 8012
"""

import logging, time, os, sys, json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.utils import generate_id
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("json_user_info_generator")
START_TIME = time.time()
profile_cache = LocalCache(namespace="user_info", ttl=900)


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class GeneratedProfile(Base):
    __tablename__ = "generated_profiles"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, index=True, nullable=False)
    profile_json = Column(Text)           # Full assembled JSON
    profile_version = Column(String, default="1.0")
    data_sources_used = Column(Text)      # JSON array of sources
    completeness_pct = Column(String)
    generated_at = Column(DateTime, default=datetime.utcnow)


# ── Profile Assembly ─────────────────────────────────────────────────────────

def assemble_profile(
    user_id: str,
    metadata: dict = None,
    eligibility: dict = None,
    trust_score: dict = None,
    anomaly_data: dict = None,
    deadlines: dict = None,
) -> dict:
    """
    Assemble a comprehensive user profile JSON from all available data sources.
    This is the single source of truth used by AI engines.
    """
    profile = {
        "user_id": user_id,
        "generated_at": datetime.utcnow().isoformat(),
        "profile_version": "1.0",
        "data_sources": [],
    }

    # ── Basic Info ────────────────────────────────
    if metadata:
        profile["personal_info"] = {
            "name": metadata.get("name"),
            "gender": metadata.get("gender"),
            "state": metadata.get("state"),
            "district": metadata.get("district"),
            "pincode": metadata.get("pincode"),
            "language_preference": metadata.get("language_preference", "en"),
        }
        profile["demographic_info"] = {
            "category": metadata.get("category"),
            "religion": metadata.get("religion"),
            "marital_status": metadata.get("marital_status"),
            "education_level": metadata.get("education_level"),
            "family_size": metadata.get("family_size"),
            "is_rural": metadata.get("is_rural"),
            "disability_status": metadata.get("disability_status"),
        }
        profile["economic_info"] = {
            "annual_income": metadata.get("annual_income"),
            "occupation": metadata.get("occupation"),
            "is_bpl": metadata.get("is_bpl"),
            "land_holding_acres": metadata.get("land_holding_acres"),
        }
        profile["derived_attributes"] = metadata.get("derived_attributes", {})
        profile["data_sources"].append("metadata_engine")

    # ── Eligibility ────────────────────────────────
    if eligibility:
        results = eligibility.get("results", [])
        profile["eligibility_summary"] = {
            "total_checked": eligibility.get("total_schemes_checked", 0),
            "eligible_count": eligibility.get("eligible", 0),
            "partial_count": eligibility.get("partial", 0),
            "schemes": [{
                "scheme_id": r.get("scheme_id"),
                "scheme_name": r.get("scheme_name"),
                "verdict": r.get("verdict"),
                "confidence": r.get("confidence"),
                "explanation": r.get("explanation"),
            } for r in results[:20]],
        }
        profile["data_sources"].append("eligibility_engine")

    # ── Trust Score ───────────────────────────────
    if trust_score:
        profile["trust_info"] = {
            "overall_score": trust_score.get("overall_score"),
            "trust_level": trust_score.get("trust_level"),
            "components": trust_score.get("components", {}),
        }
        profile["data_sources"].append("trust_scoring_engine")

    # ── Anomaly ──────────────────────────────────
    if anomaly_data:
        profile["risk_info"] = {
            "total_anomalies": anomaly_data.get("total_anomalies", 0),
            "aggregate_risk_score": anomaly_data.get("aggregate_risk_score", 0),
            "has_critical_issues": anomaly_data.get("severity_counts", {}).get("critical", 0) > 0,
        }
        profile["data_sources"].append("anomaly_detection_engine")

    # ── Deadlines ─────────────────────────────────
    if deadlines:
        alerts = deadlines.get("alerts", [])
        profile["deadline_info"] = {
            "total_upcoming": deadlines.get("total_deadlines", 0),
            "critical_count": deadlines.get("critical", 0),
            "nearest_deadlines": [{
                "scheme_name": a.get("scheme_name"),
                "deadline_date": a.get("deadline_date"),
                "days_remaining": a.get("days_remaining"),
                "urgency": a.get("urgency_score"),
            } for a in alerts[:5]],
        }
        profile["data_sources"].append("deadline_engine")

    # ── Completeness ──────────────────────────────
    total_sections = 5
    filled = len(profile["data_sources"])
    profile["completeness"] = {
        "percentage": round(filled / total_sections * 100),
        "sources_available": filled,
        "sources_total": total_sections,
        "missing": [s for s in ["metadata_engine", "eligibility_engine", "trust_scoring_engine",
                                 "anomaly_detection_engine", "deadline_engine"]
                    if s not in profile["data_sources"]],
    }

    return profile


# ── Schemas ───────────────────────────────────────────────────────────────────

class GenerateProfileRequest(BaseModel):
    user_id: str
    metadata: Optional[dict] = None
    eligibility: Optional[dict] = None
    trust_score: Optional[dict] = None
    anomaly_data: Optional[dict] = None
    deadlines: Optional[dict] = None


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 JSON User Info Generator starting...")
    await init_db()
    yield

app = FastAPI(title="AIforBharat JSON User Info Generator", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="json_user_info_generator", uptime_seconds=time.time() - START_TIME)


@app.post("/profile/generate", response_model=ApiResponse, tags=["Profile"])
async def generate_profile(data: GenerateProfileRequest):
    """
    Assemble a comprehensive user profile JSON from all data sources.
    This is the single source of truth for AI and downstream engines.
    
    Input: Partial data from various engines
    Output: Unified JSON profile with completeness metrics
    """
    profile = assemble_profile(
        user_id=data.user_id,
        metadata=data.metadata,
        eligibility=data.eligibility,
        trust_score=data.trust_score,
        anomaly_data=data.anomaly_data,
        deadlines=data.deadlines,
    )

    # Store to DB
    async with AsyncSessionLocal() as session:
        session.add(GeneratedProfile(
            id=generate_id(), user_id=data.user_id,
            profile_json=json.dumps(profile),
            data_sources_used=json.dumps(profile.get("data_sources", [])),
            completeness_pct=str(profile.get("completeness", {}).get("percentage", 0)),
        ))
        await session.commit()

    profile_cache.set(f"profile:{data.user_id}", profile)

    await event_bus.publish(EventMessage(
        event_type=EventType.PROFILE_GENERATED,
        source_engine="json_user_info_generator",
        user_id=data.user_id,
        payload={"completeness": profile.get("completeness", {}).get("percentage", 0)},
    ))

    return ApiResponse(data=profile)


@app.get("/profile/{user_id}", response_model=ApiResponse, tags=["Profile"])
async def get_profile(user_id: str):
    """Get the latest generated profile for a user."""
    cached = profile_cache.get(f"profile:{user_id}")
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(GeneratedProfile)
            .where(GeneratedProfile.user_id == user_id)
            .order_by(GeneratedProfile.generated_at.desc())
        )).scalars().first()
        if not row:
            raise HTTPException(status_code=404, detail="No generated profile found")
        profile = json.loads(row.profile_json)
        profile_cache.set(f"profile:{user_id}", profile)
        return ApiResponse(data=profile)


@app.get("/profile/{user_id}/summary", response_model=ApiResponse, tags=["Profile"])
async def get_profile_summary(user_id: str):
    """Get a compact summary suitable for AI prompts."""
    cached = profile_cache.get(f"profile:{user_id}")
    if not cached:
        async with AsyncSessionLocal() as session:
            row = (await session.execute(
                select(GeneratedProfile)
                .where(GeneratedProfile.user_id == user_id)
                .order_by(GeneratedProfile.generated_at.desc())
            )).scalars().first()
            if not row:
                raise HTTPException(status_code=404, detail="No profile found")
            cached = json.loads(row.profile_json)

    # Build compact summary
    pi = cached.get("personal_info", {})
    ei = cached.get("economic_info", {})
    da = cached.get("derived_attributes", {})
    es = cached.get("eligibility_summary", {})

    summary_lines = []
    if pi.get("name"):
        summary_lines.append(f"Name: {pi['name']}")
    if pi.get("state"):
        summary_lines.append(f"State: {pi['state']}")
    if da.get("age"):
        summary_lines.append(f"Age: {da['age']} ({da.get('age_group', '')})")
    if ei.get("annual_income") is not None:
        summary_lines.append(f"Income: ₹{ei['annual_income']:,.0f} ({da.get('income_bracket', '')})")
    if ei.get("occupation"):
        summary_lines.append(f"Occupation: {ei['occupation']}")
    if es.get("eligible_count"):
        summary_lines.append(f"Eligible schemes: {es['eligible_count']}/{es.get('total_checked', 0)}")

    return ApiResponse(data={
        "user_id": user_id,
        "summary_text": "\n".join(summary_lines),
        "completeness": cached.get("completeness", {}).get("percentage", 0),
    })
