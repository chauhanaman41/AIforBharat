"""
AIforBharat — Analytics Warehouse (Engine 13)
==============================================
Aggregates platform-wide analytics: user demographics, scheme popularity,
eligibility distributions, system performance metrics, funnel analysis.
Stores analytical summaries locally in SQLite. Subscribes to events
from the in-memory event bus.

Port: 8013
"""

import logging, time, os, sys, json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List
from collections import Counter

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, select, func

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.utils import generate_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("analytics_warehouse")
START_TIME = time.time()


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    id = Column(String, primary_key=True, default=generate_id)
    event_type = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True)
    engine = Column(String, index=True)
    payload = Column(Text)              # JSON
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    id = Column(String, primary_key=True, default=generate_id)
    metric_name = Column(String, index=True, nullable=False)
    metric_value = Column(Float, nullable=False)
    dimension = Column(String, index=True)   # state, scheme, engine, etc.
    dimension_value = Column(String, index=True)
    period = Column(String, default="daily")  # daily, weekly, monthly
    snapshot_date = Column(DateTime, default=datetime.utcnow)


class FunnelStep(Base):
    __tablename__ = "funnel_steps"
    id = Column(String, primary_key=True, default=generate_id)
    funnel_name = Column(String, index=True, nullable=False)
    step_name = Column(String, nullable=False)
    step_order = Column(Integer, nullable=False)
    user_id = Column(String, index=True)
    completed_at = Column(DateTime, default=datetime.utcnow)


# ── In-Memory Counters ───────────────────────────────────────────────────────

_event_counters: Counter = Counter()
_scheme_popularity: Counter = Counter()
_engine_calls: Counter = Counter()
_user_actions: Counter = Counter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class RecordEventRequest(BaseModel):
    event_type: str
    user_id: Optional[str] = None
    engine: Optional[str] = None
    payload: dict = {}


class RecordMetricRequest(BaseModel):
    metric_name: str
    metric_value: float
    dimension: str = "global"
    dimension_value: str = "all"


class FunnelStepRequest(BaseModel):
    funnel_name: str
    step_name: str
    step_order: int
    user_id: str


class DateRangeQuery(BaseModel):
    start_date: Optional[str] = None   # ISO format
    end_date: Optional[str] = None
    dimension: Optional[str] = None


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Analytics Warehouse starting...")
    await init_db()
    _subscribe_events()
    yield

app = FastAPI(title="AIforBharat Analytics Warehouse", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


def _subscribe_events():
    """Subscribe to event bus for automatic analytics ingestion."""
    async def _on_event(msg: dict):
        event_type = msg.get("event_type", "unknown")
        _event_counters[event_type] += 1
        user_id = msg.get("data", {}).get("user_id")
        engine = msg.get("source")
        if engine:
            _engine_calls[engine] += 1
        if user_id:
            _user_actions[user_id] += 1
        scheme = msg.get("data", {}).get("scheme_name") or msg.get("data", {}).get("scheme")
        if scheme:
            _scheme_popularity[scheme] += 1

    event_bus.subscribe("*", _on_event)
    logger.info("Subscribed to all events for analytics")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="analytics_warehouse", uptime_seconds=time.time() - START_TIME)


@app.post("/analytics/events", response_model=ApiResponse, tags=["Events"])
async def record_event(data: RecordEventRequest):
    """Record an analytics event."""
    _event_counters[data.event_type] += 1
    if data.engine:
        _engine_calls[data.engine] += 1
    if data.user_id:
        _user_actions[data.user_id] += 1

    async with AsyncSessionLocal() as session:
        session.add(AnalyticsEvent(
            id=generate_id(), event_type=data.event_type,
            user_id=data.user_id, engine=data.engine,
            payload=json.dumps(data.payload),
        ))
        await session.commit()
    return ApiResponse(message="Event recorded")


@app.post("/analytics/metrics", response_model=ApiResponse, tags=["Metrics"])
async def record_metric(data: RecordMetricRequest):
    """Record a metric snapshot."""
    async with AsyncSessionLocal() as session:
        session.add(MetricSnapshot(
            id=generate_id(), metric_name=data.metric_name,
            metric_value=data.metric_value,
            dimension=data.dimension, dimension_value=data.dimension_value,
        ))
        await session.commit()
    return ApiResponse(message="Metric recorded")


@app.post("/analytics/funnel", response_model=ApiResponse, tags=["Funnel"])
async def record_funnel_step(data: FunnelStepRequest):
    """Record user progress through a funnel."""
    async with AsyncSessionLocal() as session:
        session.add(FunnelStep(
            id=generate_id(), funnel_name=data.funnel_name,
            step_name=data.step_name, step_order=data.step_order,
            user_id=data.user_id,
        ))
        await session.commit()
    return ApiResponse(message="Funnel step recorded")


@app.get("/analytics/dashboard", response_model=ApiResponse, tags=["Dashboard"])
async def dashboard_summary():
    """Platform-wide analytics dashboard summary."""
    async with AsyncSessionLocal() as session:
        total_events = (await session.execute(
            select(func.count(AnalyticsEvent.id))
        )).scalar() or 0
        unique_users = (await session.execute(
            select(func.count(func.distinct(AnalyticsEvent.user_id)))
        )).scalar() or 0
        top_events = _event_counters.most_common(10)
        top_schemes = _scheme_popularity.most_common(10)
        top_engines = _engine_calls.most_common(10)

    return ApiResponse(data={
        "total_events": total_events + sum(_event_counters.values()),
        "unique_users": unique_users + len(_user_actions),
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "top_event_types": [{"type": k, "count": v} for k, v in top_events],
        "top_schemes": [{"scheme": k, "count": v} for k, v in top_schemes],
        "top_engines": [{"engine": k, "count": v} for k, v in top_engines],
    })


@app.get("/analytics/events/query", response_model=ApiResponse, tags=["Events"])
async def query_events(
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    engine: Optional[str] = None,
    limit: int = Query(50, le=500),
):
    """Query analytics events with filters."""
    async with AsyncSessionLocal() as session:
        query = select(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc())
        if event_type:
            query = query.where(AnalyticsEvent.event_type == event_type)
        if user_id:
            query = query.where(AnalyticsEvent.user_id == user_id)
        if engine:
            query = query.where(AnalyticsEvent.engine == engine)
        rows = (await session.execute(query.limit(limit))).scalars().all()
        return ApiResponse(data=[{
            "id": r.id, "event_type": r.event_type,
            "user_id": r.user_id, "engine": r.engine,
            "payload": json.loads(r.payload) if r.payload else {},
            "created_at": r.created_at.isoformat(),
        } for r in rows])


@app.get("/analytics/metrics/query", response_model=ApiResponse, tags=["Metrics"])
async def query_metrics(
    metric_name: Optional[str] = None,
    dimension: Optional[str] = None,
    limit: int = Query(50, le=500),
):
    """Query metric snapshots."""
    async with AsyncSessionLocal() as session:
        query = select(MetricSnapshot).order_by(MetricSnapshot.snapshot_date.desc())
        if metric_name:
            query = query.where(MetricSnapshot.metric_name == metric_name)
        if dimension:
            query = query.where(MetricSnapshot.dimension == dimension)
        rows = (await session.execute(query.limit(limit))).scalars().all()
        return ApiResponse(data=[{
            "metric_name": r.metric_name, "value": r.metric_value,
            "dimension": r.dimension, "dimension_value": r.dimension_value,
            "date": r.snapshot_date.isoformat(),
        } for r in rows])


@app.get("/analytics/funnel/{funnel_name}", response_model=ApiResponse, tags=["Funnel"])
async def get_funnel(funnel_name: str):
    """Get funnel analysis showing drop-off at each step."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(FunnelStep).where(FunnelStep.funnel_name == funnel_name)
        )).scalars().all()

        step_users: dict[int, set] = {}
        step_names: dict[int, str] = {}
        for r in rows:
            step_users.setdefault(r.step_order, set()).add(r.user_id)
            step_names[r.step_order] = r.step_name

        sorted_steps = sorted(step_users.keys())
        analysis = []
        for i, step in enumerate(sorted_steps):
            count = len(step_users[step])
            prev_count = len(step_users[sorted_steps[i - 1]]) if i > 0 else count
            drop_off = round(1 - (count / prev_count), 3) if prev_count > 0 and i > 0 else 0
            analysis.append({
                "step_order": step, "step_name": step_names.get(step, f"Step {step}"),
                "users": count, "drop_off_rate": drop_off,
            })
        return ApiResponse(data={"funnel": funnel_name, "steps": analysis})


@app.get("/analytics/scheme-popularity", response_model=ApiResponse, tags=["Schemes"])
async def scheme_popularity():
    """Get scheme popularity rankings from event data."""
    return ApiResponse(data=[
        {"scheme": k, "interactions": v}
        for k, v in _scheme_popularity.most_common(50)
    ])
