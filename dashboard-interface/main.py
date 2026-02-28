"""
AIforBharat — Dashboard Interface (Engine 14)
==============================================
Backend-for-Frontend (BFF) layer that aggregates data from all
engines into consolidated endpoints for the dashboard UI.
Provides widgets, charts, navigation, and user-facing summaries.

Port: 8014
"""

import logging, time, os, sys, json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage
from shared.event_bus import event_bus
from shared.utils import generate_id, create_access_token, decode_token
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("dashboard_interface")
START_TIME = time.time()
dash_cache = LocalCache(namespace="dashboard", ttl=300)


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class DashboardPreference(Base):
    __tablename__ = "dashboard_preferences"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, index=True, unique=True, nullable=False)
    theme = Column(String, default="light")
    language = Column(String, default="english")
    widget_order = Column(Text, default="[]")   # JSON array
    notifications_enabled = Column(String, default="true")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Schemas ───────────────────────────────────────────────────────────────────

class PreferenceUpdate(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    widget_order: Optional[list] = None
    notifications_enabled: Optional[bool] = None


# ── Widget builders ──────────────────────────────────────────────────────────

def _build_eligibility_widget(user_id: str) -> dict:
    """Eligibility summary widget."""
    return {
        "widget": "eligibility_summary",
        "title": "Your Eligibility",
        "data_url": f"/eligibility/check",
        "refresh_seconds": 600,
        "icon": "shield-check",
    }


def _build_schemes_widget() -> dict:
    return {
        "widget": "popular_schemes",
        "title": "Popular Schemes",
        "data_url": "/schemes/popular",
        "refresh_seconds": 3600,
        "icon": "trending-up",
    }


def _build_deadlines_widget(user_id: str) -> dict:
    return {
        "widget": "upcoming_deadlines",
        "title": "Upcoming Deadlines",
        "data_url": f"/deadlines/check",
        "refresh_seconds": 1800,
        "icon": "clock",
    }


def _build_trust_widget(user_id: str) -> dict:
    return {
        "widget": "trust_score",
        "title": "Trust Score",
        "data_url": f"/trust/score/{user_id}",
        "refresh_seconds": 3600,
        "icon": "award",
    }


def _build_profile_widget(user_id: str) -> dict:
    return {
        "widget": "profile_completeness",
        "title": "Profile Completeness",
        "data_url": f"/profile/generate/{user_id}",
        "refresh_seconds": 900,
        "icon": "user-check",
    }


def _build_simulation_widget() -> dict:
    return {
        "widget": "what_if",
        "title": "What-If Simulator",
        "data_url": "/simulation/what-if",
        "refresh_seconds": 0,
        "icon": "sliders",
    }


def _build_ai_chat_widget() -> dict:
    return {
        "widget": "ai_assistant",
        "title": "AI Assistant",
        "data_url": "/neural/chat",
        "refresh_seconds": 0,
        "icon": "message-circle",
    }


def _build_voice_widget() -> dict:
    return {
        "widget": "voice_assistant",
        "title": "Voice Assistant",
        "data_url": "/speech/query",
        "refresh_seconds": 0,
        "icon": "mic",
        "languages": ["hindi", "english", "tamil", "telugu", "bengali"],
    }


DEFAULT_WIDGETS = [
    "eligibility_summary", "popular_schemes", "upcoming_deadlines",
    "trust_score", "profile_completeness", "what_if",
    "ai_assistant", "voice_assistant",
]


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Dashboard Interface starting...")
    await init_db()
    yield

app = FastAPI(title="AIforBharat Dashboard Interface", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="dashboard_interface", uptime_seconds=time.time() - START_TIME)


@app.get("/dashboard/home/{user_id}", response_model=ApiResponse, tags=["Dashboard"])
async def dashboard_home(user_id: str):
    """
    Main dashboard view — aggregates widgets, quick stats, and navigation
    for the given user. All data sourced from local engines.
    """
    cached = dash_cache.get(f"home:{user_id}")
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    widgets = [
        _build_eligibility_widget(user_id),
        _build_schemes_widget(),
        _build_deadlines_widget(user_id),
        _build_trust_widget(user_id),
        _build_profile_widget(user_id),
        _build_simulation_widget(),
        _build_ai_chat_widget(),
        _build_voice_widget(),
    ]

    result = {
        "user_id": user_id,
        "widgets": widgets,
        "navigation": [
            {"label": "Home", "path": "/", "icon": "home"},
            {"label": "My Schemes", "path": "/schemes", "icon": "file-text"},
            {"label": "Eligibility", "path": "/eligibility", "icon": "check-circle"},
            {"label": "Documents", "path": "/documents", "icon": "folder"},
            {"label": "Simulator", "path": "/simulator", "icon": "sliders"},
            {"label": "AI Chat", "path": "/chat", "icon": "message-circle"},
            {"label": "Voice", "path": "/voice", "icon": "mic"},
            {"label": "Analytics", "path": "/analytics", "icon": "bar-chart"},
            {"label": "Settings", "path": "/settings", "icon": "settings"},
        ],
        "quick_actions": [
            {"label": "Check Eligibility", "action": "check_eligibility", "icon": "search"},
            {"label": "Ask AI", "action": "open_chat", "icon": "message-circle"},
            {"label": "Upload Document", "action": "upload_doc", "icon": "upload"},
            {"label": "Voice Query", "action": "voice_query", "icon": "mic"},
        ],
    }

    dash_cache.set(f"home:{user_id}", result)
    return ApiResponse(data=result)


@app.get("/dashboard/schemes", response_model=ApiResponse, tags=["Dashboard"])
async def schemes_overview():
    """Schemes listing page data."""
    # Aggregated from policy-fetching-engine seed data
    schemes = [
        {"id": "pm-kisan", "name": "PM-KISAN", "category": "Agriculture", "beneficiaries": "14 Cr+", "status": "Active"},
        {"id": "pmay", "name": "Pradhan Mantri Awas Yojana", "category": "Housing", "beneficiaries": "4 Cr+", "status": "Active"},
        {"id": "pmjay", "name": "Ayushman Bharat (PMJAY)", "category": "Health", "beneficiaries": "55 Cr+", "status": "Active"},
        {"id": "ujjwala", "name": "PM Ujjwala Yojana", "category": "Energy", "beneficiaries": "10 Cr+", "status": "Active"},
        {"id": "mudra", "name": "PM MUDRA Yojana", "category": "Finance", "beneficiaries": "40 Cr+", "status": "Active"},
        {"id": "pmsby", "name": "PM Suraksha Bima Yojana", "category": "Insurance", "beneficiaries": "35 Cr+", "status": "Active"},
        {"id": "pmjjby", "name": "PM Jeevan Jyoti Bima Yojana", "category": "Insurance", "beneficiaries": "16 Cr+", "status": "Active"},
        {"id": "ssy", "name": "Sukanya Samriddhi Yojana", "category": "Savings", "beneficiaries": "3 Cr+", "status": "Active"},
        {"id": "nps", "name": "National Pension System", "category": "Pension", "beneficiaries": "7 Cr+", "status": "Active"},
        {"id": "scst-scholarship", "name": "SC/ST Post-Matric Scholarship", "category": "Education", "beneficiaries": "60 L+", "status": "Active"},
    ]
    return ApiResponse(data={"schemes": schemes, "total": len(schemes)})


@app.get("/dashboard/engines/status", response_model=ApiResponse, tags=["System"])
async def engines_status():
    """Health status of all 21 engines."""
    engines = [
        {"id": 1, "name": "Login & Register", "port": settings.LOGIN_REGISTER_PORT, "path": "login-register-engine"},
        {"id": 2, "name": "Identity Engine", "port": settings.IDENTITY_ENGINE_PORT, "path": "identity-engine"},
        {"id": 3, "name": "Raw Data Store", "port": settings.RAW_DATA_STORE_PORT, "path": "raw-data-store"},
        {"id": 4, "name": "Metadata Engine", "port": settings.METADATA_ENGINE_PORT, "path": "metadata-engine"},
        {"id": 5, "name": "Processed Metadata Store", "port": settings.PROCESSED_METADATA_PORT, "path": "processed-user-metadata-store"},
        {"id": 6, "name": "Vector Database", "port": settings.VECTOR_DATABASE_PORT, "path": "vector-database"},
        {"id": 7, "name": "Neural Network", "port": settings.NEURAL_NETWORK_PORT, "path": "neural-network-engine"},
        {"id": 8, "name": "Anomaly Detection", "port": settings.ANOMALY_DETECTION_PORT, "path": "anomaly-detection-engine"},
        {"id": 9, "name": "API Gateway", "port": settings.API_GATEWAY_PORT, "path": "api-gateway"},
        {"id": 10, "name": "Chunks Engine", "port": settings.CHUNKS_ENGINE_PORT, "path": "chunks-engine"},
        {"id": 11, "name": "Policy Fetching", "port": settings.POLICY_FETCHING_PORT, "path": "policy-fetching-engine"},
        {"id": 12, "name": "JSON User Info Gen", "port": settings.JSON_USER_INFO_PORT, "path": "json-user-info-generator"},
        {"id": 13, "name": "Analytics Warehouse", "port": settings.ANALYTICS_WAREHOUSE_PORT, "path": "analytics-warehouse"},
        {"id": 14, "name": "Dashboard Interface", "port": settings.DASHBOARD_BFF_PORT, "path": "dashboard-interface"},
        {"id": 15, "name": "Eligibility Rules", "port": settings.ELIGIBILITY_RULES_PORT, "path": "eligibility-rules-engine"},
        {"id": 16, "name": "Deadline Monitoring", "port": settings.DEADLINE_MONITORING_PORT, "path": "deadline-monitoring-engine"},
        {"id": 17, "name": "Simulation Engine", "port": settings.SIMULATION_ENGINE_PORT, "path": "simulation-engine"},
        {"id": 18, "name": "Gov Data Sync", "port": settings.GOV_DATA_SYNC_PORT, "path": "government-data-sync-engine"},
        {"id": 19, "name": "Trust Scoring", "port": settings.TRUST_SCORING_PORT, "path": "trust-scoring-engine"},
        {"id": 20, "name": "Speech Interface", "port": settings.SPEECH_INTERFACE_PORT, "path": "speech-interface-engine"},
        {"id": 21, "name": "Document Understanding", "port": settings.DOC_UNDERSTANDING_PORT, "path": "document-understanding-engine"},
    ]
    return ApiResponse(data={"engines": engines, "total": 21})


@app.get("/dashboard/preferences/{user_id}", response_model=ApiResponse, tags=["Preferences"])
async def get_preferences(user_id: str):
    """Get user dashboard preferences."""
    async with AsyncSessionLocal() as session:
        pref = (await session.execute(
            select(DashboardPreference).where(DashboardPreference.user_id == user_id)
        )).scalar_one_or_none()
        if not pref:
            return ApiResponse(data={
                "user_id": user_id, "theme": "light", "language": "english",
                "widget_order": DEFAULT_WIDGETS, "notifications_enabled": True,
            })
        return ApiResponse(data={
            "user_id": pref.user_id, "theme": pref.theme,
            "language": pref.language,
            "widget_order": json.loads(pref.widget_order),
            "notifications_enabled": pref.notifications_enabled == "true",
        })


@app.put("/dashboard/preferences/{user_id}", response_model=ApiResponse, tags=["Preferences"])
async def update_preferences(user_id: str, data: PreferenceUpdate):
    """Update user dashboard preferences."""
    async with AsyncSessionLocal() as session:
        pref = (await session.execute(
            select(DashboardPreference).where(DashboardPreference.user_id == user_id)
        )).scalar_one_or_none()
        if not pref:
            pref = DashboardPreference(id=generate_id(), user_id=user_id)
            session.add(pref)
        if data.theme is not None:
            pref.theme = data.theme
        if data.language is not None:
            pref.language = data.language
        if data.widget_order is not None:
            pref.widget_order = json.dumps(data.widget_order)
        if data.notifications_enabled is not None:
            pref.notifications_enabled = "true" if data.notifications_enabled else "false"
        pref.updated_at = datetime.utcnow()
        await session.commit()

    dash_cache.delete(f"home:{user_id}")
    return ApiResponse(message="Preferences updated")


@app.get("/dashboard/search", response_model=ApiResponse, tags=["Search"])
async def global_search(q: str = Query(..., min_length=2)):
    """
    Global search across schemes, features, and engines.
    Local keyword-based search (no external API dependency).
    """
    q_lower = q.lower()
    results = []

    # Search schemes
    scheme_keywords = {
        "pm-kisan": ["kisan", "farmer", "agriculture", "pm kisan"],
        "pmay": ["housing", "awas", "pmay", "home"],
        "pmjay": ["health", "ayushman", "pmjay", "hospital", "insurance"],
        "ujjwala": ["lpg", "gas", "ujjwala", "cooking"],
        "mudra": ["loan", "mudra", "business", "msme"],
        "pmsby": ["suraksha", "accident", "pmsby"],
        "nps": ["pension", "nps", "retirement"],
        "ssy": ["sukanya", "girl", "daughter", "savings"],
    }
    for scheme_id, keywords in scheme_keywords.items():
        if any(kw in q_lower for kw in keywords):
            results.append({"type": "scheme", "id": scheme_id, "label": scheme_id.upper()})

    # Search features
    feature_keywords = {
        "eligibility": {"type": "feature", "path": "/eligibility", "label": "Check Eligibility"},
        "simulate": {"type": "feature", "path": "/simulator", "label": "What-If Simulator"},
        "chat": {"type": "feature", "path": "/chat", "label": "AI Chat Assistant"},
        "voice": {"type": "feature", "path": "/voice", "label": "Voice Assistant"},
        "document": {"type": "feature", "path": "/documents", "label": "Document Upload"},
        "deadline": {"type": "feature", "path": "/deadlines", "label": "Deadline Tracker"},
    }
    for kw, feat in feature_keywords.items():
        if kw in q_lower:
            results.append(feat)

    return ApiResponse(data={"query": q, "results": results, "count": len(results)})
