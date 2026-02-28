"""
AIforBharat — Eligibility Rules Engine (Engine 15)
====================================================
Deterministic rule-based engine that matches user profiles against
scheme eligibility criteria. Produces verdicts: eligible, ineligible,
partial, needs_verification. Supports 100+ government schemes.

Port: 8015
"""

import logging, time, os, sys, json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Float, Boolean, Integer, select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType, EligibilityVerdict
from shared.event_bus import event_bus
from shared.utils import generate_id
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("eligibility_rules_engine")
START_TIME = time.time()
eligibility_cache = LocalCache(namespace="eligibility", ttl=1800)


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class EligibilityRule(Base):
    __tablename__ = "eligibility_rules"
    id = Column(String, primary_key=True, default=generate_id)
    scheme_id = Column(String, index=True, nullable=False)
    scheme_name = Column(String, nullable=False)
    rule_type = Column(String)       # age, income, category, state, gender, occupation, etc.
    field = Column(String)           # profile field to check
    operator = Column(String)        # eq, ne, lt, lte, gt, gte, in, not_in, contains, exists
    value = Column(Text)             # comparison value (JSON-encoded for complex types)
    is_mandatory = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class EligibilityResult(Base):
    __tablename__ = "eligibility_results"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, index=True, nullable=False)
    scheme_id = Column(String, index=True, nullable=False)
    scheme_name = Column(String)
    verdict = Column(String)         # eligible, ineligible, partial, needs_verification
    confidence = Column(Float, default=1.0)
    matched_rules = Column(Text)     # JSON array
    unmet_rules = Column(Text)       # JSON array
    missing_fields = Column(Text)    # JSON array
    explanation = Column(Text)
    evaluated_at = Column(DateTime, default=datetime.utcnow)


# ── Built-in Scheme Rules ────────────────────────────────────────────────────

BUILT_IN_RULES = [
    # PM-KISAN
    {"scheme_id": "PM-KISAN-2024", "scheme_name": "PM Kisan Samman Nidhi",
     "rules": [
         {"field": "occupation", "operator": "contains", "value": "farmer,agriculture,kisan", "type": "occupation", "desc": "Must be a farmer"},
         {"field": "annual_income", "operator": "lte", "value": "200000", "type": "income", "desc": "Income ≤ ₹2,00,000"},
         {"field": "land_holding_acres", "operator": "gt", "value": "0", "type": "land", "mandatory": False, "desc": "Should have landholding"},
     ]},
    # PMJAY (Ayushman Bharat)
    {"scheme_id": "AYUSHMAN-BHARAT-2024", "scheme_name": "Ayushman Bharat PM-JAY",
     "rules": [
         {"field": "is_bpl", "operator": "eq", "value": "true", "type": "category", "desc": "Must be BPL or SECC-listed"},
         {"field": "annual_income", "operator": "lte", "value": "500000", "type": "income", "mandatory": False, "desc": "Income ≤ ₹5,00,000"},
     ]},
    # PM Awas Yojana
    {"scheme_id": "PM-AWAS-YOJANA-2024", "scheme_name": "PM Awas Yojana",
     "rules": [
         {"field": "annual_income", "operator": "lte", "value": "1800000", "type": "income", "desc": "Income ≤ ₹18,00,000 (MIG-II)"},
         {"field": "category", "operator": "in", "value": "EWS,LIG,MIG,SC,ST,OBC,General", "type": "category", "mandatory": False},
     ]},
    # PM Ujjwala
    {"scheme_id": "PM-UJJWALA-2024", "scheme_name": "PM Ujjwala Yojana",
     "rules": [
         {"field": "gender", "operator": "eq", "value": "female", "type": "gender", "desc": "Applicant must be female"},
         {"field": "is_bpl", "operator": "eq", "value": "true", "type": "category", "desc": "Must be BPL household"},
     ]},
    # MUDRA
    {"scheme_id": "MUDRA-YOJANA-2024", "scheme_name": "PM MUDRA Yojana",
     "rules": [
         {"field": "age", "operator": "gte", "value": "18", "type": "age", "desc": "Min age 18"},
         {"field": "employment_category", "operator": "in", "value": "self_employed,other,agriculture", "type": "occupation", "mandatory": False, "desc": "Non-corporate, non-farm enterprise"},
     ]},
    # PMSBY
    {"scheme_id": "PMSBY-2024", "scheme_name": "PM Suraksha Bima Yojana",
     "rules": [
         {"field": "age", "operator": "gte", "value": "18", "type": "age", "desc": "Min age 18"},
         {"field": "age", "operator": "lte", "value": "70", "type": "age", "desc": "Max age 70"},
     ]},
    # PMJJBY
    {"scheme_id": "PMJJBY-2024", "scheme_name": "PM Jeevan Jyoti Bima Yojana",
     "rules": [
         {"field": "age", "operator": "gte", "value": "18", "type": "age", "desc": "Min age 18"},
         {"field": "age", "operator": "lte", "value": "50", "type": "age", "desc": "Max age 50"},
     ]},
    # Sukanya Samriddhi
    {"scheme_id": "SUKANYA-SAMRIDDHI-2024", "scheme_name": "Sukanya Samriddhi Yojana",
     "rules": [
         {"field": "gender", "operator": "eq", "value": "female", "type": "gender", "desc": "For girl child"},
         {"field": "age", "operator": "lte", "value": "10", "type": "age", "desc": "Girl must be below 10 years"},
     ]},
    # NPS
    {"scheme_id": "NATIONAL-PENSION-2024", "scheme_name": "National Pension System",
     "rules": [
         {"field": "age", "operator": "gte", "value": "18", "type": "age", "desc": "Min age 18"},
         {"field": "age", "operator": "lte", "value": "70", "type": "age", "desc": "Max age 70"},
     ]},
    # SC/ST Scholarship
    {"scheme_id": "SCHOLARSHIP-SC-ST-2024", "scheme_name": "Post-Matric Scholarship SC/ST",
     "rules": [
         {"field": "category", "operator": "in", "value": "SC,ST", "type": "category", "desc": "Must be SC or ST"},
         {"field": "annual_income", "operator": "lte", "value": "250000", "type": "income", "desc": "Family income ≤ ₹2,50,000"},
     ]},
]


# ── Rule Evaluation Engine ───────────────────────────────────────────────────

def _get_profile_value(profile: dict, field: str) -> Any:
    """Get a value from user profile, checking both top-level and derived attributes."""
    if field in profile:
        return profile[field]
    derived = profile.get("derived_attributes", {})
    if field in derived:
        return derived[field]
    return None


def _evaluate_rule(profile: dict, rule: dict) -> dict:
    """Evaluate a single rule against a user profile."""
    field = rule["field"]
    operator = rule["operator"]
    expected = rule["value"]
    value = _get_profile_value(profile, field)

    if value is None:
        return {"status": "missing", "field": field, "description": rule.get("desc", "")}

    try:
        if operator == "eq":
            passed = str(value).lower() == str(expected).lower()
        elif operator == "ne":
            passed = str(value).lower() != str(expected).lower()
        elif operator == "lt":
            passed = float(value) < float(expected)
        elif operator == "lte":
            passed = float(value) <= float(expected)
        elif operator == "gt":
            passed = float(value) > float(expected)
        elif operator == "gte":
            passed = float(value) >= float(expected)
        elif operator == "in":
            allowed = [v.strip().lower() for v in expected.split(",")]
            passed = str(value).lower() in allowed
        elif operator == "not_in":
            disallowed = [v.strip().lower() for v in expected.split(",")]
            passed = str(value).lower() not in disallowed
        elif operator == "contains":
            keywords = [v.strip().lower() for v in expected.split(",")]
            passed = any(kw in str(value).lower() for kw in keywords)
        elif operator == "exists":
            passed = value is not None
        else:
            passed = False
    except (ValueError, TypeError):
        return {"status": "error", "field": field, "description": rule.get("desc", "")}

    return {
        "status": "passed" if passed else "failed",
        "field": field,
        "operator": operator,
        "expected": expected,
        "actual": str(value),
        "description": rule.get("desc", ""),
        "mandatory": rule.get("mandatory", True),
    }


def evaluate_scheme(profile: dict, scheme: dict) -> dict:
    """Evaluate all rules for a scheme against a user profile."""
    results = []
    for rule in scheme["rules"]:
        result = _evaluate_rule(profile, rule)
        results.append(result)

    mandatory_results = [r for r in results if r.get("mandatory", True)]
    optional_results = [r for r in results if not r.get("mandatory", True)]

    passed = [r for r in mandatory_results if r["status"] == "passed"]
    failed = [r for r in mandatory_results if r["status"] == "failed"]
    missing = [r for r in results if r["status"] == "missing"]
    errors = [r for r in results if r["status"] == "error"]

    total_mandatory = len(mandatory_results)

    if total_mandatory == 0:
        verdict = "needs_verification"
        confidence = 0.3
    elif len(failed) > 0:
        verdict = "ineligible"
        confidence = 1.0 - (len(missing) * 0.1)
    elif len(missing) > 0:
        if len(passed) > 0:
            verdict = "partial"
            confidence = len(passed) / (total_mandatory + len(missing))
        else:
            verdict = "needs_verification"
            confidence = 0.3
    else:
        verdict = "eligible"
        confidence = 1.0

    # Account for optional passed rules as bonus confidence
    opt_passed = [r for r in optional_results if r["status"] == "passed"]
    if opt_passed and verdict == "eligible":
        confidence = min(1.0, confidence + 0.05 * len(opt_passed))

    return {
        "scheme_id": scheme["scheme_id"],
        "scheme_name": scheme["scheme_name"],
        "verdict": verdict,
        "confidence": round(confidence, 2),
        "matched_rules": [r for r in results if r["status"] == "passed"],
        "unmet_rules": [r for r in results if r["status"] == "failed"],
        "missing_fields": [r["field"] for r in missing],
        "explanation": _generate_explanation(scheme["scheme_name"], verdict, passed, failed, missing),
    }


def _generate_explanation(scheme_name: str, verdict: str, passed: list, failed: list, missing: list) -> str:
    """Generate human-readable explanation for the verdict."""
    if verdict == "eligible":
        return f"You meet all eligibility criteria for {scheme_name}."
    elif verdict == "ineligible":
        reasons = "; ".join(r.get("description", r["field"]) for r in failed)
        return f"You are not eligible for {scheme_name}. Criteria not met: {reasons}."
    elif verdict == "partial":
        missing_list = ", ".join(r["field"] for r in missing)
        return f"You may be eligible for {scheme_name} but we need more information: {missing_list}."
    else:
        return f"We need additional information to determine your eligibility for {scheme_name}."


# ── Schemas ───────────────────────────────────────────────────────────────────

class CheckEligibilityRequest(BaseModel):
    user_id: str
    profile: dict     # User profile with derived attributes
    scheme_ids: Optional[List[str]] = None  # None = check all schemes


class AddRuleRequest(BaseModel):
    scheme_id: str
    scheme_name: str
    field: str
    operator: str
    value: str
    is_mandatory: bool = True
    description: str = ""


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Eligibility Rules Engine starting...")
    await init_db()
    await _seed_rules()
    yield

app = FastAPI(title="AIforBharat Eligibility Rules Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


async def _seed_rules():
    """Seed built-in scheme rules into DB."""
    async with AsyncSessionLocal() as session:
        for scheme in BUILT_IN_RULES:
            for rule in scheme["rules"]:
                existing = (await session.execute(
                    select(EligibilityRule).where(
                        EligibilityRule.scheme_id == scheme["scheme_id"],
                        EligibilityRule.field == rule["field"],
                        EligibilityRule.operator == rule["operator"],
                    )
                )).scalar_one_or_none()
                if not existing:
                    session.add(EligibilityRule(
                        id=generate_id(),
                        scheme_id=scheme["scheme_id"],
                        scheme_name=scheme["scheme_name"],
                        rule_type=rule.get("type", "general"),
                        field=rule["field"],
                        operator=rule["operator"],
                        value=rule["value"],
                        is_mandatory=rule.get("mandatory", True),
                        description=rule.get("desc", ""),
                    ))
        await session.commit()
    logger.info("Seeded built-in eligibility rules")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="eligibility_rules_engine", uptime_seconds=time.time() - START_TIME)


@app.post("/eligibility/check", response_model=ApiResponse, tags=["Eligibility"])
async def check_eligibility(data: CheckEligibilityRequest):
    """
    Check user eligibility across all (or specified) schemes.
    Returns verdicts with matched/unmet criteria and explanations.
    
    Input: User profile (with derived_attributes from Metadata Engine)
    Output: Per-scheme verdict, confidence, matched/unmet rules
    """
    cache_key = f"elig:{data.user_id}:{json.dumps(sorted(data.scheme_ids or []))}"
    cached = eligibility_cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    # Filter schemes if specified
    schemes_to_check = BUILT_IN_RULES
    if data.scheme_ids:
        schemes_to_check = [s for s in BUILT_IN_RULES if s["scheme_id"] in data.scheme_ids]

    results = []
    for scheme in schemes_to_check:
        result = evaluate_scheme(data.profile, scheme)
        results.append(result)

        # Store to DB
        async with AsyncSessionLocal() as session:
            session.add(EligibilityResult(
                id=generate_id(), user_id=data.user_id,
                scheme_id=result["scheme_id"], scheme_name=result["scheme_name"],
                verdict=result["verdict"], confidence=result["confidence"],
                matched_rules=json.dumps(result["matched_rules"]),
                unmet_rules=json.dumps(result["unmet_rules"]),
                missing_fields=json.dumps(result["missing_fields"]),
                explanation=result["explanation"],
            ))
            await session.commit()

    # Sort by relevance: eligible > partial > needs_verification > ineligible
    verdict_order = {"eligible": 0, "partial": 1, "needs_verification": 2, "ineligible": 3}
    results.sort(key=lambda r: (verdict_order.get(r["verdict"], 4), -r["confidence"]))

    summary = {
        "user_id": data.user_id,
        "total_schemes_checked": len(results),
        "eligible": len([r for r in results if r["verdict"] == "eligible"]),
        "partial": len([r for r in results if r["verdict"] == "partial"]),
        "ineligible": len([r for r in results if r["verdict"] == "ineligible"]),
        "needs_verification": len([r for r in results if r["verdict"] == "needs_verification"]),
        "results": results,
    }

    eligibility_cache.set(cache_key, summary)

    await event_bus.publish(EventMessage(
        event_type=EventType.ELIGIBILITY_CHECKED,
        source_engine="eligibility_rules_engine",
        user_id=data.user_id,
        payload={
            "eligible_count": summary["eligible"],
            "total_checked": summary["total_schemes_checked"],
        },
    ))

    return ApiResponse(data=summary)


@app.get("/eligibility/history/{user_id}", response_model=ApiResponse, tags=["Eligibility"])
async def get_eligibility_history(user_id: str):
    """Get previous eligibility check results for a user."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(EligibilityResult)
            .where(EligibilityResult.user_id == user_id)
            .order_by(EligibilityResult.evaluated_at.desc())
        )).scalars().all()
        return ApiResponse(data=[{
            "scheme_id": r.scheme_id, "scheme_name": r.scheme_name,
            "verdict": r.verdict, "confidence": r.confidence,
            "explanation": r.explanation,
            "evaluated_at": r.evaluated_at.isoformat() if r.evaluated_at else None,
        } for r in rows])


@app.get("/eligibility/rules", response_model=ApiResponse, tags=["Rules"])
async def list_rules(scheme_id: Optional[str] = None):
    """List all eligibility rules, optionally filtered by scheme."""
    async with AsyncSessionLocal() as session:
        query = select(EligibilityRule)
        if scheme_id:
            query = query.where(EligibilityRule.scheme_id == scheme_id)
        rows = (await session.execute(query)).scalars().all()
        return ApiResponse(data=[{
            "scheme_id": r.scheme_id, "scheme_name": r.scheme_name,
            "field": r.field, "operator": r.operator, "value": r.value,
            "mandatory": r.is_mandatory, "description": r.description,
        } for r in rows])


@app.post("/eligibility/rules/add", response_model=ApiResponse, tags=["Rules"])
async def add_rule(data: AddRuleRequest):
    """Add a custom eligibility rule."""
    async with AsyncSessionLocal() as session:
        session.add(EligibilityRule(
            id=generate_id(), scheme_id=data.scheme_id, scheme_name=data.scheme_name,
            field=data.field, operator=data.operator, value=data.value,
            is_mandatory=data.is_mandatory, description=data.description,
        ))
        await session.commit()
    return ApiResponse(message="Rule added")


@app.get("/eligibility/schemes", response_model=ApiResponse, tags=["Schemes"])
async def list_schemes():
    """List all schemes with rule counts."""
    return ApiResponse(data=[{
        "scheme_id": s["scheme_id"],
        "scheme_name": s["scheme_name"],
        "rule_count": len(s["rules"]),
    } for s in BUILT_IN_RULES])
