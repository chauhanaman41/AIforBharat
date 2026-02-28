"""
AIforBharat — Trust Scoring Engine (Engine 19)
================================================
Computes composite trust scores for users based on:
- Data completeness
- Anomaly history
- Document verification status (stubbed)
- Behavioral signals (login frequency, profile updates)
- Cross-reference consistency

Trust levels: UNVERIFIED, LOW, MEDIUM, HIGH, VERIFIED

Port: 8019
"""

import logging, time, os, sys, json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, select, func

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType, TrustLevel
from shared.event_bus import event_bus
from shared.utils import generate_id
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("trust_scoring_engine")
START_TIME = time.time()
trust_cache = LocalCache(namespace="trust", ttl=600)


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class TrustScoreRecord(Base):
    __tablename__ = "trust_scores"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, index=True, nullable=False)
    overall_score = Column(Float, default=0.0)     # 0.0 - 100.0
    trust_level = Column(String, default="UNVERIFIED")
    data_completeness_score = Column(Float, default=0.0)
    anomaly_score = Column(Float, default=0.0)     # 0 = no anomalies, higher = worse
    consistency_score = Column(Float, default=0.0)
    behavior_score = Column(Float, default=0.0)
    verification_score = Column(Float, default=0.0)
    component_details = Column(Text)    # JSON breakdown
    factors_positive = Column(Text)     # JSON array
    factors_negative = Column(Text)     # JSON array
    computed_at = Column(DateTime, default=datetime.utcnow)


# ── Trust Computation ────────────────────────────────────────────────────────

# Required fields for completeness scoring
CRITICAL_FIELDS = ["name", "phone", "state", "date_of_birth", "gender"]
IMPORTANT_FIELDS = ["district", "pincode", "annual_income", "occupation", "category"]
OPTIONAL_FIELDS = ["education_level", "marital_status", "family_size", "religion", "disability_status", "land_holding_acres"]


def compute_data_completeness(profile: dict) -> tuple:
    """Score data completeness (0-100)."""
    score = 0
    total_weight = 0
    positive_factors = []
    negative_factors = []

    # Critical fields (weight 3 each)
    for f in CRITICAL_FIELDS:
        total_weight += 3
        if profile.get(f):
            score += 3
            positive_factors.append(f"Core field '{f}' provided")
        else:
            negative_factors.append(f"Missing critical field: {f}")

    # Important fields (weight 2 each)
    for f in IMPORTANT_FIELDS:
        total_weight += 2
        if profile.get(f) is not None:
            score += 2
            positive_factors.append(f"Field '{f}' provided")
        else:
            negative_factors.append(f"Missing field: {f}")

    # Optional fields (weight 1 each)
    for f in OPTIONAL_FIELDS:
        total_weight += 1
        if profile.get(f) is not None:
            score += 1

    pct = round((score / max(total_weight, 1)) * 100, 1)
    return pct, positive_factors, negative_factors


def compute_anomaly_factor(anomaly_data: dict) -> tuple:
    """Convert anomaly results to a trust factor (0-100 where 100 = clean)."""
    if not anomaly_data or anomaly_data.get("total_anomalies", 0) == 0:
        return 100.0, ["No anomalies detected"]

    risk = anomaly_data.get("aggregate_risk_score", 0)
    count = anomaly_data.get("total_anomalies", 0)
    severity = anomaly_data.get("severity_counts", {})

    # Deduct points based on anomalies
    deduction = 0
    deduction += severity.get("critical", 0) * 30
    deduction += severity.get("high", 0) * 20
    deduction += severity.get("medium", 0) * 10
    deduction += severity.get("low", 0) * 5

    score = max(0, 100 - deduction)
    factors = [f"{count} anomaly(ies) found"]
    if "critical" in severity:
        factors.append(f"{severity['critical']} critical issue(s)")
    return score, factors


def compute_consistency(profile: dict) -> tuple:
    """Check internal consistency of profile data."""
    score = 100.0
    factors = []
    da = profile.get("derived_attributes", {})

    # Age vs education consistency
    age = da.get("age")
    edu = profile.get("education_level", "").lower()
    if age and age < 15 and edu in ["graduate", "post_graduate", "phd"]:
        score -= 20
        factors.append("Age inconsistent with education level")

    # Income vs BPL flag
    income = profile.get("annual_income")
    is_bpl = profile.get("is_bpl")
    if is_bpl and income and income > 50000:
        score -= 15
        factors.append("BPL flag inconsistent with declared income")

    if not factors:
        factors.append("Profile data is internally consistent")

    return max(0, score), factors


def compute_trust_level(overall_score: float) -> str:
    """Map overall score to trust level."""
    if overall_score >= 85:
        return "VERIFIED"
    elif overall_score >= 70:
        return "HIGH"
    elif overall_score >= 50:
        return "MEDIUM"
    elif overall_score >= 30:
        return "LOW"
    else:
        return "UNVERIFIED"


def compute_full_trust_score(
    profile: dict,
    anomaly_data: dict = None,
    behavior_data: dict = None,
) -> dict:
    """Compute composite trust score from all factors."""
    # Data completeness (weight: 30%)
    completeness, pos_comp, neg_comp = compute_data_completeness(profile)

    # Anomaly factor (weight: 25%)
    anomaly_score, anomaly_factors = compute_anomaly_factor(anomaly_data or {})

    # Consistency (weight: 20%)
    consistency, consistency_factors = compute_consistency(profile)

    # Behavior (weight: 15%) — stub for now
    behavior = 50.0  # Neutral default
    behavior_factors = ["Behavioral scoring not yet available"]
    if behavior_data:
        logins = behavior_data.get("login_count", 0)
        behavior = min(100, 50 + logins * 5)
        behavior_factors = [f"{logins} login(s) recorded"]

    # Verification (weight: 10%) — stubbed (no DigiLocker)
    verification = 0.0
    verification_factors = ["Document verification not available (DigiLocker integration pending)"]

    # Weighted composite
    overall = round(
        completeness * 0.30 +
        anomaly_score * 0.25 +
        consistency * 0.20 +
        behavior * 0.15 +
        verification * 0.10,
        1
    )

    trust_level = compute_trust_level(overall)

    positive = pos_comp + [f for f in anomaly_factors if "No anomalies" in f] + [f for f in consistency_factors if "consistent" in f]
    negative = neg_comp + [f for f in anomaly_factors if "anomaly" in f.lower()] + [f for f in consistency_factors if "inconsistent" in f.lower()] + verification_factors

    return {
        "overall_score": overall,
        "trust_level": trust_level,
        "components": {
            "data_completeness": {"score": completeness, "weight": "30%"},
            "anomaly_check": {"score": anomaly_score, "weight": "25%"},
            "consistency": {"score": consistency, "weight": "20%"},
            "behavior": {"score": behavior, "weight": "15%"},
            "verification": {"score": verification, "weight": "10%"},
        },
        "positive_factors": positive[:10],
        "negative_factors": negative[:10],
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class ComputeTrustRequest(BaseModel):
    user_id: str
    profile: dict
    anomaly_data: Optional[dict] = None
    behavior_data: Optional[dict] = None


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Trust Scoring Engine starting...")
    await init_db()
    yield

app = FastAPI(title="AIforBharat Trust Scoring Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="trust_scoring_engine", uptime_seconds=time.time() - START_TIME)


@app.post("/trust/compute", response_model=ApiResponse, tags=["Trust"])
async def compute_trust(data: ComputeTrustRequest):
    """
    Compute composite trust score for a user.
    
    Input: User profile + optional anomaly data + behavior data
    Output: Overall score (0-100), trust level, component breakdown
    """
    result = compute_full_trust_score(data.profile, data.anomaly_data, data.behavior_data)

    # Store to DB
    async with AsyncSessionLocal() as session:
        session.add(TrustScoreRecord(
            id=generate_id(), user_id=data.user_id,
            overall_score=result["overall_score"],
            trust_level=result["trust_level"],
            data_completeness_score=result["components"]["data_completeness"]["score"],
            anomaly_score=result["components"]["anomaly_check"]["score"],
            consistency_score=result["components"]["consistency"]["score"],
            behavior_score=result["components"]["behavior"]["score"],
            verification_score=result["components"]["verification"]["score"],
            component_details=json.dumps(result["components"]),
            factors_positive=json.dumps(result["positive_factors"]),
            factors_negative=json.dumps(result["negative_factors"]),
        ))
        await session.commit()

    trust_cache.set(f"trust:{data.user_id}", result)

    await event_bus.publish(EventMessage(
        event_type=EventType.TRUST_SCORE_UPDATED,
        source_engine="trust_scoring_engine",
        user_id=data.user_id,
        payload={"score": result["overall_score"], "level": result["trust_level"]},
    ))

    return ApiResponse(data=result)


@app.get("/trust/user/{user_id}", response_model=ApiResponse, tags=["Trust"])
async def get_trust_score(user_id: str):
    """Get latest trust score for a user."""
    cached = trust_cache.get(f"trust:{user_id}")
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(TrustScoreRecord)
            .where(TrustScoreRecord.user_id == user_id)
            .order_by(TrustScoreRecord.computed_at.desc())
        )).scalars().first()
        if not row:
            raise HTTPException(status_code=404, detail="No trust score found")
        return ApiResponse(data={
            "overall_score": row.overall_score,
            "trust_level": row.trust_level,
            "components": json.loads(row.component_details or "{}"),
            "positive_factors": json.loads(row.factors_positive or "[]"),
            "negative_factors": json.loads(row.factors_negative or "[]"),
            "computed_at": row.computed_at.isoformat() if row.computed_at else None,
        })


@app.get("/trust/user/{user_id}/history", response_model=ApiResponse, tags=["History"])
async def trust_history(user_id: str, limit: int = 20):
    """Get trust score history for a user."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(TrustScoreRecord)
            .where(TrustScoreRecord.user_id == user_id)
            .order_by(TrustScoreRecord.computed_at.desc())
            .limit(limit)
        )).scalars().all()
        return ApiResponse(data=[{
            "score": r.overall_score, "level": r.trust_level,
            "computed_at": r.computed_at.isoformat() if r.computed_at else None,
        } for r in rows])
