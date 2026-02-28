"""
AIforBharat — Deadline Monitoring Engine (Engine 16)
=====================================================
Tracks and monitors government scheme deadlines, application windows,
renewal dates. Provides countdown timers, urgency scoring, and
user-specific deadline alerts (logged locally, no push notifications).

Port: 8016
"""

import logging, time, os, sys, json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, date
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Float, Boolean, Integer, select, and_

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType, DeadlinePriority
from shared.event_bus import event_bus
from shared.utils import generate_id
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("deadline_monitoring_engine")
START_TIME = time.time()
deadline_cache = LocalCache(namespace="deadlines", ttl=600)


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class SchemeDeadline(Base):
    __tablename__ = "scheme_deadlines"
    id = Column(String, primary_key=True, default=generate_id)
    scheme_id = Column(String, index=True, nullable=False)
    scheme_name = Column(String)
    deadline_type = Column(String)          # application, renewal, document_submission, enrollment
    deadline_date = Column(DateTime, nullable=False)
    opens_at = Column(DateTime)             # When application window opens
    description = Column(String)
    ministry = Column(String)
    states_applicable = Column(Text)        # JSON array, empty = all India
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String)     # yearly, quarterly, monthly
    priority = Column(String, default="medium")  # critical, high, medium, low
    source_url = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class UserDeadlineAlert(Base):
    __tablename__ = "user_deadline_alerts"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, index=True, nullable=False)
    deadline_id = Column(String, index=True, nullable=False)
    scheme_id = Column(String)
    scheme_name = Column(String)
    alert_status = Column(String, default="pending")  # pending, acknowledged, expired, applied
    days_remaining = Column(Integer)
    urgency_score = Column(Float)           # 0.0 - 1.0
    logged_at = Column(DateTime, default=datetime.utcnow)


# ── Seed Data ────────────────────────────────────────────────────────────────

SEED_DEADLINES = [
    {
        "scheme_id": "PM-KISAN-2024",
        "scheme_name": "PM Kisan Samman Nidhi",
        "deadline_type": "renewal",
        "deadline_date": "2025-03-31",
        "description": "eKYC renewal deadline for PM-KISAN installment",
        "ministry": "Agriculture",
        "is_recurring": True,
        "recurrence_pattern": "quarterly",
        "priority": "high",
    },
    {
        "scheme_id": "AYUSHMAN-BHARAT-2024",
        "scheme_name": "Ayushman Bharat PM-JAY",
        "deadline_type": "enrollment",
        "deadline_date": "2025-12-31",
        "description": "Open enrollment for Ayushman Bharat health insurance",
        "ministry": "Health and Family Welfare",
        "is_recurring": True,
        "recurrence_pattern": "yearly",
        "priority": "medium",
    },
    {
        "scheme_id": "PM-AWAS-YOJANA-2024",
        "scheme_name": "PM Awas Yojana Urban",
        "deadline_type": "application",
        "deadline_date": "2025-06-30",
        "description": "PMAY-U Phase IV application deadline",
        "ministry": "Housing and Urban Affairs",
        "priority": "high",
    },
    {
        "scheme_id": "SCHOLARSHIP-SC-ST-2024",
        "scheme_name": "Post-Matric Scholarship SC/ST",
        "deadline_type": "application",
        "deadline_date": "2025-10-31",
        "description": "Fresh/renewal applications for FY 2025-26",
        "ministry": "Social Justice",
        "is_recurring": True,
        "recurrence_pattern": "yearly",
        "priority": "high",
    },
    {
        "scheme_id": "PMSBY-2024",
        "scheme_name": "PM Suraksha Bima Yojana",
        "deadline_type": "renewal",
        "deadline_date": "2025-05-31",
        "description": "Annual renewal auto-debit consent",
        "ministry": "Finance",
        "is_recurring": True,
        "recurrence_pattern": "yearly",
        "priority": "medium",
    },
]


def _compute_urgency(deadline_date: datetime, priority: str = "medium") -> float:
    """Compute urgency score (0.0 - 1.0) based on days remaining and priority."""
    now = datetime.utcnow()
    days = (deadline_date - now).days

    # Base score from days remaining
    if days <= 0:
        base = 1.0
    elif days <= 3:
        base = 0.95
    elif days <= 7:
        base = 0.85
    elif days <= 14:
        base = 0.7
    elif days <= 30:
        base = 0.5
    elif days <= 60:
        base = 0.3
    elif days <= 90:
        base = 0.2
    else:
        base = 0.1

    # Priority multiplier
    multipliers = {"critical": 1.0, "high": 0.9, "medium": 0.7, "low": 0.5}
    multiplier = multipliers.get(priority, 0.7)

    return round(min(1.0, base * (1 + (1 - multiplier) * 0.3)), 2)


# ── Schemas ───────────────────────────────────────────────────────────────────

class AddDeadlineRequest(BaseModel):
    scheme_id: str
    scheme_name: str
    deadline_type: str = "application"
    deadline_date: str  # YYYY-MM-DD
    opens_at: Optional[str] = None
    description: str = ""
    ministry: str = ""
    states_applicable: List[str] = []
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    priority: str = "medium"
    source_url: Optional[str] = None


class CheckDeadlinesRequest(BaseModel):
    user_id: str
    scheme_ids: Optional[List[str]] = None
    state: Optional[str] = None
    days_ahead: int = Field(default=90, ge=1, le=365)


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Deadline Monitoring Engine starting...")
    await init_db()
    await _seed_deadlines()
    yield

app = FastAPI(title="AIforBharat Deadline Monitoring Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


async def _seed_deadlines():
    """Seed initial deadline data."""
    async with AsyncSessionLocal() as session:
        for dl in SEED_DEADLINES:
            exists = (await session.execute(
                select(SchemeDeadline).where(
                    SchemeDeadline.scheme_id == dl["scheme_id"],
                    SchemeDeadline.deadline_type == dl["deadline_type"],
                )
            )).scalar_one_or_none()
            if not exists:
                session.add(SchemeDeadline(
                    id=generate_id(),
                    scheme_id=dl["scheme_id"],
                    scheme_name=dl["scheme_name"],
                    deadline_type=dl["deadline_type"],
                    deadline_date=datetime.strptime(dl["deadline_date"], "%Y-%m-%d"),
                    description=dl.get("description", ""),
                    ministry=dl.get("ministry", ""),
                    is_recurring=dl.get("is_recurring", False),
                    recurrence_pattern=dl.get("recurrence_pattern"),
                    priority=dl.get("priority", "medium"),
                ))
        await session.commit()
    logger.info("Seeded deadline data")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="deadline_monitoring_engine", uptime_seconds=time.time() - START_TIME)


@app.post("/deadlines/check", response_model=ApiResponse, tags=["Deadlines"])
async def check_deadlines(data: CheckDeadlinesRequest):
    """
    Check upcoming deadlines for a user's eligible schemes.
    Returns deadlines within days_ahead, sorted by urgency.
    Alerts are logged locally (no push notifications per constraints).
    """
    cache_key = f"dl:{data.user_id}:{data.days_ahead}"
    cached = deadline_cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    now = datetime.utcnow()
    cutoff = now + timedelta(days=data.days_ahead)

    async with AsyncSessionLocal() as session:
        query = select(SchemeDeadline).where(
            SchemeDeadline.is_active == True,
            SchemeDeadline.deadline_date >= now,
            SchemeDeadline.deadline_date <= cutoff,
        )
        if data.scheme_ids:
            query = query.where(SchemeDeadline.scheme_id.in_(data.scheme_ids))

        rows = (await session.execute(query.order_by(SchemeDeadline.deadline_date))).scalars().all()

        alerts = []
        for row in rows:
            days_remaining = (row.deadline_date - now).days
            urgency = _compute_urgency(row.deadline_date, row.priority)

            alert = {
                "deadline_id": row.id,
                "scheme_id": row.scheme_id,
                "scheme_name": row.scheme_name,
                "deadline_type": row.deadline_type,
                "deadline_date": row.deadline_date.strftime("%Y-%m-%d"),
                "days_remaining": days_remaining,
                "urgency_score": urgency,
                "priority": row.priority,
                "description": row.description,
                "ministry": row.ministry,
                "is_recurring": row.is_recurring,
            }
            alerts.append(alert)

            # Log alert locally (no notifications per constraints)
            session.add(UserDeadlineAlert(
                id=generate_id(), user_id=data.user_id,
                deadline_id=row.id, scheme_id=row.scheme_id,
                scheme_name=row.scheme_name, days_remaining=days_remaining,
                urgency_score=urgency,
            ))

        await session.commit()

    # Sort by urgency
    alerts.sort(key=lambda a: (-a["urgency_score"], a["days_remaining"]))

    result = {
        "user_id": data.user_id,
        "checked_at": now.isoformat(),
        "total_deadlines": len(alerts),
        "critical": len([a for a in alerts if a["urgency_score"] >= 0.85]),
        "upcoming_7_days": len([a for a in alerts if a["days_remaining"] <= 7]),
        "alerts": alerts,
    }

    deadline_cache.set(cache_key, result)

    await event_bus.publish(EventMessage(
        event_type=EventType.DEADLINE_APPROACHING,
        source_engine="deadline_monitoring_engine",
        user_id=data.user_id,
        payload={"total_deadlines": len(alerts), "critical": result["critical"]},
    ))

    return ApiResponse(data=result)


@app.get("/deadlines/list", response_model=ApiResponse, tags=["Deadlines"])
async def list_deadlines(
    active_only: bool = True,
    scheme_id: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    """List all tracked deadlines."""
    async with AsyncSessionLocal() as session:
        query = select(SchemeDeadline).order_by(SchemeDeadline.deadline_date)
        if active_only:
            query = query.where(SchemeDeadline.is_active == True)
        if scheme_id:
            query = query.where(SchemeDeadline.scheme_id == scheme_id)
        query = query.limit(limit)

        rows = (await session.execute(query)).scalars().all()
        return ApiResponse(data=[{
            "id": r.id, "scheme_id": r.scheme_id, "scheme_name": r.scheme_name,
            "deadline_type": r.deadline_type,
            "deadline_date": r.deadline_date.strftime("%Y-%m-%d") if r.deadline_date else None,
            "days_remaining": (r.deadline_date - datetime.utcnow()).days if r.deadline_date else None,
            "urgency": _compute_urgency(r.deadline_date, r.priority) if r.deadline_date else 0,
            "priority": r.priority, "description": r.description,
            "is_recurring": r.is_recurring,
        } for r in rows])


@app.post("/deadlines/add", response_model=ApiResponse, tags=["Deadlines"])
async def add_deadline(data: AddDeadlineRequest):
    """Add a new deadline to track."""
    async with AsyncSessionLocal() as session:
        session.add(SchemeDeadline(
            id=generate_id(), scheme_id=data.scheme_id, scheme_name=data.scheme_name,
            deadline_type=data.deadline_type,
            deadline_date=datetime.strptime(data.deadline_date, "%Y-%m-%d"),
            opens_at=datetime.strptime(data.opens_at, "%Y-%m-%d") if data.opens_at else None,
            description=data.description, ministry=data.ministry,
            states_applicable=json.dumps(data.states_applicable),
            is_recurring=data.is_recurring, recurrence_pattern=data.recurrence_pattern,
            priority=data.priority, source_url=data.source_url,
        ))
        await session.commit()
    return ApiResponse(message="Deadline added")


@app.get("/deadlines/user/{user_id}/history", response_model=ApiResponse, tags=["History"])
async def get_user_alert_history(user_id: str):
    """Get deadline alert history for a user."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(UserDeadlineAlert)
            .where(UserDeadlineAlert.user_id == user_id)
            .order_by(UserDeadlineAlert.logged_at.desc())
            .limit(100)
        )).scalars().all()
        return ApiResponse(data=[{
            "scheme_id": r.scheme_id, "scheme_name": r.scheme_name,
            "days_remaining": r.days_remaining, "urgency": r.urgency_score,
            "status": r.alert_status,
            "logged_at": r.logged_at.isoformat() if r.logged_at else None,
        } for r in rows])
