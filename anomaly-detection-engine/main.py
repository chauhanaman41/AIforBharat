"""
AIforBharat — Anomaly Detection Engine (Engine 8)
===================================================
Detects anomalies in user data, application patterns, and system behavior.
Checks for: duplicate identities, income inconsistencies, suspicious
activity patterns, data quality issues. Feeds into Trust Scoring Engine.

Port: 8008
"""

import logging, time, os, sys, json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Float, Boolean, Integer, select, func

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType, AnomalyScore
from shared.event_bus import event_bus
from shared.utils import generate_id
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("anomaly_detection_engine")
START_TIME = time.time()
anomaly_cache = LocalCache(namespace="anomaly", ttl=600)


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class AnomalyRecord(Base):
    __tablename__ = "anomaly_records"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, index=True)
    anomaly_type = Column(String, nullable=False)  # duplicate_identity, income_mismatch, suspicious_activity, data_quality, rapid_changes
    severity = Column(String, default="medium")     # low, medium, high, critical
    score = Column(Float, default=0.0)              # 0.0 - 1.0
    description = Column(Text)
    evidence = Column(Text)                          # JSON evidence details
    field_affected = Column(String)
    resolution_status = Column(String, default="open")  # open, investigating, resolved, false_positive
    resolved_at = Column(DateTime)
    resolver_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Anomaly Detection Rules ─────────────────────────────────────────────────

def check_income_anomalies(profile: dict) -> List[dict]:
    """Check for income-related anomalies."""
    anomalies = []
    income = profile.get("annual_income")
    occupation = profile.get("occupation", "").lower()
    da = profile.get("derived_attributes", {})

    if income is not None:
        # Suspiciously round income
        if income > 0 and income % 100000 == 0 and income >= 1000000:
            anomalies.append({
                "type": "income_mismatch",
                "severity": "low",
                "score": 0.3,
                "description": "Income is a very round number, may need verification",
                "field": "annual_income",
                "evidence": {"income": income},
            })

        # Income vs occupation mismatch
        if occupation and income:
            if any(k in occupation for k in ["student", "unemployed"]) and income > 300000:
                anomalies.append({
                    "type": "income_mismatch",
                    "severity": "high",
                    "score": 0.8,
                    "description": f"Occupation '{occupation}' inconsistent with income ₹{income}",
                    "field": "annual_income",
                    "evidence": {"income": income, "occupation": occupation},
                })

            if any(k in occupation for k in ["farmer", "agriculture"]) and income > 1500000:
                anomalies.append({
                    "type": "income_mismatch",
                    "severity": "medium",
                    "score": 0.6,
                    "description": "Agricultural income unusually high for individual farmer",
                    "field": "annual_income",
                    "evidence": {"income": income, "occupation": occupation},
                })

        # BPL claim with high income
        if profile.get("is_bpl") and income and income > 50000:
            anomalies.append({
                "type": "income_mismatch",
                "severity": "high",
                "score": 0.85,
                "description": "Claims BPL status but income exceeds BPL threshold",
                "field": "is_bpl",
                "evidence": {"is_bpl": True, "income": income},
            })

    return anomalies


def check_age_anomalies(profile: dict) -> List[dict]:
    """Check for age-related anomalies."""
    anomalies = []
    da = profile.get("derived_attributes", {})
    age = da.get("age")

    if age is not None:
        if age < 0 or age > 150:
            anomalies.append({
                "type": "data_quality",
                "severity": "critical",
                "score": 1.0,
                "description": f"Invalid age: {age}",
                "field": "date_of_birth",
                "evidence": {"age": age},
            })

        # Minor with spouse/employment
        if age < 18:
            if profile.get("marital_status") == "married":
                anomalies.append({
                    "type": "data_quality",
                    "severity": "high",
                    "score": 0.9,
                    "description": "Minor listed as married",
                    "field": "marital_status",
                    "evidence": {"age": age, "marital_status": "married"},
                })

    return anomalies


def check_data_quality(profile: dict) -> List[dict]:
    """Check data quality issues."""
    anomalies = []

    # Pincode format
    pincode = profile.get("pincode", "")
    if pincode and (not pincode.isdigit() or len(pincode) != 6):
        anomalies.append({
            "type": "data_quality", "severity": "medium", "score": 0.5,
            "description": f"Invalid pincode format: {pincode}",
            "field": "pincode",
            "evidence": {"pincode": pincode},
        })

    # Phone format
    phone = profile.get("phone", "")
    if phone and (not phone.isdigit() or len(phone) != 10 or phone[0] not in "6789"):
        anomalies.append({
            "type": "data_quality", "severity": "medium", "score": 0.5,
            "description": "Invalid phone number format",
            "field": "phone",
            "evidence": {"phone_length": len(phone)},
        })

    # Family size outlier
    fam = profile.get("family_size")
    if fam is not None and (fam <= 0 or fam > 25):
        anomalies.append({
            "type": "data_quality", "severity": "medium", "score": 0.6,
            "description": f"Unusual family size: {fam}",
            "field": "family_size",
            "evidence": {"family_size": fam},
        })

    # Land holding outlier
    land = profile.get("land_holding_acres")
    if land is not None and land > 100:
        anomalies.append({
            "type": "data_quality", "severity": "medium", "score": 0.5,
            "description": f"Very large landholding: {land} acres",
            "field": "land_holding_acres",
            "evidence": {"land_acres": land},
        })

    return anomalies


def check_duplicate_patterns(profile: dict, existing_profiles: List[dict] = None) -> List[dict]:
    """Check for potential duplicate/fraudulent registrations."""
    anomalies = []
    # In production, this would compare against other profiles
    # For local-first, we flag patterns that suggest duplicates
    name = profile.get("name", "")
    if name and len(name.strip()) < 2:
        anomalies.append({
            "type": "duplicate_identity", "severity": "medium", "score": 0.5,
            "description": "Name too short, possible placeholder",
            "field": "name",
            "evidence": {"name": name},
        })
    return anomalies


def run_full_check(profile: dict) -> dict:
    """Run all anomaly detection checks on a profile."""
    all_anomalies = []
    all_anomalies.extend(check_income_anomalies(profile))
    all_anomalies.extend(check_age_anomalies(profile))
    all_anomalies.extend(check_data_quality(profile))
    all_anomalies.extend(check_duplicate_patterns(profile))

    # Compute aggregate risk score
    if all_anomalies:
        max_score = max(a["score"] for a in all_anomalies)
        avg_score = sum(a["score"] for a in all_anomalies) / len(all_anomalies)
        aggregate_score = round(0.6 * max_score + 0.4 * avg_score, 3)
    else:
        aggregate_score = 0.0

    severity_counts = {}
    for a in all_anomalies:
        sev = a["severity"]
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        "total_anomalies": len(all_anomalies),
        "aggregate_risk_score": aggregate_score,
        "severity_counts": severity_counts,
        "anomalies": all_anomalies,
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class AnomalyCheckRequest(BaseModel):
    user_id: str
    profile: dict


class ResolveAnomalyRequest(BaseModel):
    status: str = "resolved"    # resolved, false_positive
    notes: str = ""


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Anomaly Detection Engine starting...")
    await init_db()
    yield

app = FastAPI(title="AIforBharat Anomaly Detection Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="anomaly_detection_engine", uptime_seconds=time.time() - START_TIME)


@app.post("/anomaly/check", response_model=ApiResponse, tags=["Detection"])
async def check_anomalies(data: AnomalyCheckRequest):
    """
    Run anomaly detection on a user profile.
    Checks: income mismatches, age anomalies, data quality, duplicate patterns.
    
    Input: User profile with derived attributes
    Output: List of detected anomalies with severity and scores
    """
    result = run_full_check(data.profile)

    # Store anomalies to DB
    async with AsyncSessionLocal() as session:
        for a in result["anomalies"]:
            session.add(AnomalyRecord(
                id=generate_id(), user_id=data.user_id,
                anomaly_type=a["type"], severity=a["severity"],
                score=a["score"], description=a["description"],
                evidence=json.dumps(a.get("evidence", {})),
                field_affected=a.get("field"),
            ))
        await session.commit()

    if result["aggregate_risk_score"] > 0.5:
        await event_bus.publish(EventMessage(
            event_type=EventType.ANOMALY_DETECTED,
            source_engine="anomaly_detection_engine",
            user_id=data.user_id,
            payload={
                "risk_score": result["aggregate_risk_score"],
                "anomaly_count": result["total_anomalies"],
            },
        ))

    return ApiResponse(data=result)


@app.get("/anomaly/user/{user_id}", response_model=ApiResponse, tags=["Query"])
async def get_user_anomalies(user_id: str, status: Optional[str] = None):
    """Get all anomaly records for a user."""
    async with AsyncSessionLocal() as session:
        query = select(AnomalyRecord).where(AnomalyRecord.user_id == user_id)
        if status:
            query = query.where(AnomalyRecord.resolution_status == status)
        rows = (await session.execute(
            query.order_by(AnomalyRecord.created_at.desc())
        )).scalars().all()
        return ApiResponse(data=[{
            "id": r.id, "type": r.anomaly_type, "severity": r.severity,
            "score": r.score, "description": r.description,
            "field": r.field_affected, "status": r.resolution_status,
            "evidence": json.loads(r.evidence or "{}"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows])


@app.put("/anomaly/{anomaly_id}/resolve", response_model=ApiResponse, tags=["Management"])
async def resolve_anomaly(anomaly_id: str, data: ResolveAnomalyRequest):
    """Resolve or mark an anomaly as false positive."""
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(AnomalyRecord).where(AnomalyRecord.id == anomaly_id)
        )).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Anomaly not found")
        row.resolution_status = data.status
        row.resolver_notes = data.notes
        row.resolved_at = datetime.utcnow()
        await session.commit()
    return ApiResponse(message=f"Anomaly {data.status}")


@app.get("/anomaly/stats", response_model=ApiResponse, tags=["Stats"])
async def anomaly_stats():
    """Get anomaly detection statistics."""
    async with AsyncSessionLocal() as session:
        total = (await session.execute(select(func.count(AnomalyRecord.id)))).scalar() or 0
        open_count = (await session.execute(
            select(func.count(AnomalyRecord.id)).where(AnomalyRecord.resolution_status == "open")
        )).scalar() or 0
        by_type = (await session.execute(
            select(AnomalyRecord.anomaly_type, func.count(AnomalyRecord.id))
            .group_by(AnomalyRecord.anomaly_type)
        )).all()
        by_severity = (await session.execute(
            select(AnomalyRecord.severity, func.count(AnomalyRecord.id))
            .group_by(AnomalyRecord.severity)
        )).all()

    return ApiResponse(data={
        "total_anomalies": total,
        "open": open_count,
        "by_type": {t: c for t, c in by_type},
        "by_severity": {s: c for s, c in by_severity},
    })
