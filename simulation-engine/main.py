"""
AIforBharat — Simulation Engine (Engine 17)
=============================================
What-if analysis engine. Simulates changes in user profile
(income change, marriage, new child, job change, moving states)
and recalculates scheme eligibility. Shows potential benefit
gains/losses from life events.

Port: 8017
"""

import logging, time, os, sys, json, copy
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.utils import generate_id, get_age_group, get_income_bracket
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("simulation_engine")
START_TIME = time.time()
sim_cache = LocalCache(namespace="simulations", ttl=1800)


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class SimulationRecord(Base):
    __tablename__ = "simulation_records"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, index=True, nullable=False)
    scenario_type = Column(String)           # income_change, marriage, child, relocation, etc.
    original_profile = Column(Text)          # JSON
    modified_profile = Column(Text)          # JSON
    original_eligible = Column(Text)         # JSON list of scheme_ids
    new_eligible = Column(Text)              # JSON list
    gained = Column(Text)                    # JSON list of newly eligible
    lost = Column(Text)                      # JSON list of newly ineligible
    net_benefit_change = Column(Float)       # Estimated INR change
    recommendations = Column(Text)           # JSON array
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Inline Eligibility Evaluator ─────────────────────────────────────────────

# Simplified scheme rules for simulation (same as Engine 15, but self-contained)
SCHEME_RULES = {
    "PM-KISAN-2024": {
        "name": "PM Kisan Samman Nidhi",
        "benefit_annual": 6000,
        "rules": [
            ("annual_income", "lte", 200000),
            ("employment_category", "in", ["agriculture", "self_employed"]),
        ],
    },
    "AYUSHMAN-BHARAT-2024": {
        "name": "Ayushman Bharat PM-JAY",
        "benefit_annual": 500000,   # coverage value
        "rules": [
            ("annual_income", "lte", 500000),
        ],
    },
    "PM-AWAS-YOJANA-2024": {
        "name": "PM Awas Yojana",
        "benefit_annual": 267000,   # subsidy
        "rules": [
            ("annual_income", "lte", 1800000),
        ],
    },
    "PM-UJJWALA-2024": {
        "name": "PM Ujjwala Yojana",
        "benefit_annual": 1600,
        "rules": [
            ("gender", "eq", "female"),
            ("is_bpl", "eq", True),
        ],
    },
    "MUDRA-YOJANA-2024": {
        "name": "PM MUDRA Yojana",
        "benefit_annual": 1000000,  # max loan
        "rules": [
            ("age", "gte", 18),
        ],
    },
    "PMSBY-2024": {
        "name": "PM Suraksha Bima Yojana",
        "benefit_annual": 200000,   # cover
        "rules": [
            ("age", "gte", 18), ("age", "lte", 70),
        ],
    },
    "PMJJBY-2024": {
        "name": "PM Jeevan Jyoti Bima Yojana",
        "benefit_annual": 200000,
        "rules": [
            ("age", "gte", 18), ("age", "lte", 50),
        ],
    },
    "SCHOLARSHIP-SC-ST-2024": {
        "name": "Post-Matric Scholarship SC/ST",
        "benefit_annual": 50000,    # approximate
        "rules": [
            ("category", "in", ["SC", "ST"]),
            ("annual_income", "lte", 250000),
        ],
    },
}


def _get_val(profile: dict, field: str):
    """Get value from profile or derived attributes."""
    if field in profile:
        return profile[field]
    da = profile.get("derived_attributes", {})
    return da.get(field)


def _check_eligible(profile: dict, rules: list) -> bool:
    """Check if a profile meets all rules."""
    for field, op, expected in rules:
        val = _get_val(profile, field)
        if val is None:
            continue  # Skip missing fields (lenient)
        try:
            if op == "eq":
                if str(val).lower() != str(expected).lower():
                    return False
            elif op == "lte":
                if float(val) > float(expected):
                    return False
            elif op == "gte":
                if float(val) < float(expected):
                    return False
            elif op == "in":
                if str(val) not in [str(e) for e in expected]:
                    return False
        except (ValueError, TypeError):
            pass
    return True


def get_eligible_schemes(profile: dict) -> List[str]:
    """Get list of eligible scheme IDs for a profile."""
    eligible = []
    for scheme_id, scheme in SCHEME_RULES.items():
        if _check_eligible(profile, scheme["rules"]):
            eligible.append(scheme_id)
    return eligible


def _recompute_derived(profile: dict) -> dict:
    """Recompute derived attributes after profile changes."""
    p = dict(profile)
    da = dict(p.get("derived_attributes", {}))

    if "annual_income" in p and p["annual_income"] is not None:
        da["income_bracket"] = get_income_bracket(p["annual_income"])
        da["is_bpl"] = p["annual_income"] < 27000

    if "age" in da:
        da["age_group"] = get_age_group(da["age"])
        da["is_senior_citizen"] = da["age"] >= 60
        da["is_minor"] = da["age"] < 18

    p["derived_attributes"] = da
    return p


# ── Schemas ───────────────────────────────────────────────────────────────────

class SimulateRequest(BaseModel):
    user_id: str
    current_profile: dict
    changes: dict               # Fields to modify {field: new_value}
    scenario_type: str = "custom"  # income_change, marriage, child, relocation, job_change, custom


class LifeEventRequest(BaseModel):
    user_id: str
    current_profile: dict
    life_event: str             # marriage, child_born, job_loss, retirement, relocation, promotion


class CompareRequest(BaseModel):
    user_id: str
    profile_a: dict
    profile_b: dict


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Simulation Engine starting...")
    await init_db()
    yield

app = FastAPI(title="AIforBharat Simulation Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="simulation_engine", uptime_seconds=time.time() - START_TIME)


@app.post("/simulate/what-if", response_model=ApiResponse, tags=["Simulate"])
async def simulate_what_if(data: SimulateRequest):
    """
    Simulate a what-if scenario: apply changes to current profile and
    recalculate eligibility. Shows which schemes are gained/lost.
    
    Input: Current profile + changes to apply
    Output: Gained/lost schemes, net benefit change, recommendations
    """
    # Apply changes to create modified profile
    modified = copy.deepcopy(data.current_profile)
    for field, value in data.changes.items():
        if field in modified:
            modified[field] = value
        else:
            da = modified.get("derived_attributes", {})
            da[field] = value
            modified["derived_attributes"] = da

    modified = _recompute_derived(modified)

    # Evaluate eligibility for both
    original_eligible = get_eligible_schemes(data.current_profile)
    new_eligible = get_eligible_schemes(modified)

    gained = [s for s in new_eligible if s not in original_eligible]
    lost = [s for s in original_eligible if s not in new_eligible]

    # Calculate net benefit change
    gained_benefit = sum(SCHEME_RULES[s]["benefit_annual"] for s in gained if s in SCHEME_RULES)
    lost_benefit = sum(SCHEME_RULES[s]["benefit_annual"] for s in lost if s in SCHEME_RULES)
    net_change = gained_benefit - lost_benefit

    # Generate recommendations
    recommendations = []
    if gained:
        for s in gained:
            name = SCHEME_RULES.get(s, {}).get("name", s)
            recommendations.append(f"You would become eligible for {name}")
    if lost:
        for s in lost:
            name = SCHEME_RULES.get(s, {}).get("name", s)
            recommendations.append(f"You would lose eligibility for {name}")
    if not gained and not lost:
        recommendations.append("This change would not affect your current scheme eligibility")

    # Store result
    async with AsyncSessionLocal() as session:
        session.add(SimulationRecord(
            id=generate_id(), user_id=data.user_id,
            scenario_type=data.scenario_type,
            original_profile=json.dumps(data.current_profile),
            modified_profile=json.dumps(modified),
            original_eligible=json.dumps(original_eligible),
            new_eligible=json.dumps(new_eligible),
            gained=json.dumps(gained), lost=json.dumps(lost),
            net_benefit_change=net_change,
            recommendations=json.dumps(recommendations),
        ))
        await session.commit()

    await event_bus.publish(EventMessage(
        event_type=EventType.SIMULATION_RUN,
        source_engine="simulation_engine",
        user_id=data.user_id,
        payload={"scenario": data.scenario_type, "gained": len(gained), "lost": len(lost)},
    ))

    return ApiResponse(data={
        "scenario_type": data.scenario_type,
        "changes_applied": data.changes,
        "original_eligible": [{"id": s, "name": SCHEME_RULES.get(s, {}).get("name", s)} for s in original_eligible],
        "new_eligible": [{"id": s, "name": SCHEME_RULES.get(s, {}).get("name", s)} for s in new_eligible],
        "gained": [{"id": s, "name": SCHEME_RULES.get(s, {}).get("name", s), "benefit": SCHEME_RULES.get(s, {}).get("benefit_annual", 0)} for s in gained],
        "lost": [{"id": s, "name": SCHEME_RULES.get(s, {}).get("name", s), "benefit": SCHEME_RULES.get(s, {}).get("benefit_annual", 0)} for s in lost],
        "net_benefit_change": net_change,
        "recommendations": recommendations,
    })


@app.post("/simulate/life-event", response_model=ApiResponse, tags=["Simulate"])
async def simulate_life_event(data: LifeEventRequest):
    """
    Simulate a life event and show impact on scheme eligibility.
    Predefined events: marriage, child_born, job_loss, retirement, relocation, promotion.
    """
    # Map life events to profile changes
    event_changes = {
        "marriage": {"marital_status": "married"},
        "child_born": lambda p: {"family_size": (p.get("family_size") or 1) + 1},
        "job_loss": {"annual_income": 0, "occupation": "unemployed"},
        "retirement": {"occupation": "retired", "annual_income": (data.current_profile.get("annual_income", 0) * 0.4)},
        "relocation": {},   # User should specify state change via what-if
        "promotion": {"annual_income": (data.current_profile.get("annual_income", 0) * 1.3)},
    }

    changes = event_changes.get(data.life_event, {})
    if callable(changes):
        changes = changes(data.current_profile)

    sim_req = SimulateRequest(
        user_id=data.user_id,
        current_profile=data.current_profile,
        changes=changes,
        scenario_type=data.life_event,
    )
    return await simulate_what_if(sim_req)


@app.post("/simulate/compare", response_model=ApiResponse, tags=["Simulate"])
async def compare_profiles(data: CompareRequest):
    """Compare eligibility between two different profiles."""
    eligible_a = get_eligible_schemes(data.profile_a)
    eligible_b = get_eligible_schemes(data.profile_b)

    only_a = [s for s in eligible_a if s not in eligible_b]
    only_b = [s for s in eligible_b if s not in eligible_a]
    common = [s for s in eligible_a if s in eligible_b]

    return ApiResponse(data={
        "profile_a_eligible": len(eligible_a),
        "profile_b_eligible": len(eligible_b),
        "common": [{"id": s, "name": SCHEME_RULES.get(s, {}).get("name", s)} for s in common],
        "only_profile_a": [{"id": s, "name": SCHEME_RULES.get(s, {}).get("name", s)} for s in only_a],
        "only_profile_b": [{"id": s, "name": SCHEME_RULES.get(s, {}).get("name", s)} for s in only_b],
    })


@app.get("/simulate/history/{user_id}", response_model=ApiResponse, tags=["History"])
async def get_simulation_history(user_id: str):
    """Get simulation history for a user."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(SimulationRecord)
            .where(SimulationRecord.user_id == user_id)
            .order_by(SimulationRecord.created_at.desc())
            .limit(20)
        )).scalars().all()
        return ApiResponse(data=[{
            "id": r.id, "scenario": r.scenario_type,
            "gained": json.loads(r.gained or "[]"),
            "lost": json.loads(r.lost or "[]"),
            "net_benefit_change": r.net_benefit_change,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows])
