"""
AIforBharat — Metadata Engine (Engine 4)
==========================================
Transforms raw user input into structured, normalized profiles.
Derives attributes: age_group, income_bracket, life_stage, bpl_status, etc.
Validates and normalizes state names, pincodes, and demographic data.

Port: 8004
"""

import logging, time, os, sys
from contextlib import asynccontextmanager
from datetime import datetime, date
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import init_db
from shared.models import ApiResponse, EventMessage, EventType, HealthResponse, UserProfile
from shared.event_bus import event_bus
from shared.utils import (
    generate_id, normalize_state_name, get_age_group, get_income_bracket,
    INDIAN_STATES
)
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("metadata_engine")
START_TIME = time.time()

# Cache for processed metadata
metadata_cache = LocalCache(namespace="metadata", ttl=3600)


def _compute_age(dob_str: str) -> Optional[int]:
    """Compute age from date-of-birth string (YYYY-MM-DD)."""
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except (ValueError, TypeError):
        return None


def _derive_life_stage(age: int, marital_status: str = None) -> str:
    """Derive life stage from age and marital status."""
    if age < 18:
        return "minor"
    elif age < 23:
        return "student"
    elif age < 30:
        return "early_career"
    elif age < 45:
        return "mid_career"
    elif age < 60:
        return "pre_retirement"
    else:
        return "retired"


def _derive_tax_bracket(income: float) -> str:
    """Derive tax bracket from annual income (new regime FY 2024-25)."""
    if income <= 300000:
        return "nil"
    elif income <= 700000:
        return "5%"
    elif income <= 1000000:
        return "10%"
    elif income <= 1200000:
        return "15%"
    elif income <= 1500000:
        return "20%"
    else:
        return "30%"


def _derive_employment_category(occupation: str) -> str:
    """Categorize occupation into broader employment category."""
    if not occupation:
        return "unknown"
    occ_lower = occupation.lower()
    if any(k in occ_lower for k in ["farmer", "agriculture", "farming", "kisan"]):
        return "agriculture"
    elif any(k in occ_lower for k in ["govt", "government", "sarkari", "public"]):
        return "government"
    elif any(k in occ_lower for k in ["business", "self-employed", "entrepreneur", "shop"]):
        return "self_employed"
    elif any(k in occ_lower for k in ["salaried", "private", "employee", "engineer", "doctor"]):
        return "salaried"
    elif any(k in occ_lower for k in ["student"]):
        return "student"
    elif any(k in occ_lower for k in ["retired", "pension"]):
        return "retired"
    elif any(k in occ_lower for k in ["unemployed", "job seeker"]):
        return "unemployed"
    else:
        return "other"


def process_metadata(raw_input: dict) -> dict:
    """
    Main metadata processing pipeline:
    1. Validate & normalize input fields
    2. Derive computed attributes
    3. Return enriched metadata
    """
    processed = dict(raw_input)

    # ── Step 1: Normalize ─────────────────────────────────────────
    if processed.get("state"):
        processed["state"] = normalize_state_name(processed["state"])

    if processed.get("pincode"):
        processed["pincode"] = processed["pincode"].strip()[:6]

    if processed.get("name"):
        processed["name"] = processed["name"].strip().title()

    # ── Step 2: Derive attributes ─────────────────────────────────
    derived = {}

    # Age group
    age = None
    if processed.get("date_of_birth"):
        age = _compute_age(processed["date_of_birth"])
        if age is not None:
            derived["age"] = age
            derived["age_group"] = get_age_group(age)
            derived["is_minor"] = age < 18
            derived["is_senior_citizen"] = age >= 60

    # Income bracket
    if processed.get("annual_income") is not None:
        income = float(processed["annual_income"])
        derived["income_bracket"] = get_income_bracket(income)
        derived["tax_bracket"] = _derive_tax_bracket(income)
        derived["is_bpl"] = income < 27000  # BPL threshold approximation

    # Life stage
    if age is not None:
        derived["life_stage"] = _derive_life_stage(age, processed.get("marital_status"))

    # Employment category
    if processed.get("occupation"):
        derived["employment_category"] = _derive_employment_category(processed["occupation"])

    # Category flags
    if processed.get("category"):
        cat = processed["category"].upper()
        derived["is_sc_st"] = cat in ["SC", "ST"]
        derived["is_obc"] = cat == "OBC"
        derived["is_ews"] = cat == "EWS"

    # Rural/urban
    if processed.get("is_rural") is not None:
        derived["area_type"] = "rural" if processed["is_rural"] else "urban"

    # Farming-specific
    if processed.get("land_holding_acres") is not None:
        acres = float(processed["land_holding_acres"])
        if acres <= 0:
            derived["farmer_category"] = "landless"
        elif acres <= 2.5:
            derived["farmer_category"] = "marginal"
        elif acres <= 5:
            derived["farmer_category"] = "small"
        elif acres <= 10:
            derived["farmer_category"] = "semi_medium"
        else:
            derived["farmer_category"] = "large"

    processed["derived_attributes"] = derived
    processed["metadata_version"] = "1.0"
    processed["processed_at"] = datetime.utcnow().isoformat()

    return processed


# ── Schemas ───────────────────────────────────────────────────────────────────

class MetadataProcessRequest(BaseModel):
    user_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    pincode: Optional[str] = None
    annual_income: Optional[float] = None
    occupation: Optional[str] = None
    category: Optional[str] = None
    religion: Optional[str] = None
    marital_status: Optional[str] = None
    education_level: Optional[str] = None
    family_size: Optional[int] = None
    is_bpl: Optional[bool] = None
    is_rural: Optional[bool] = None
    disability_status: Optional[str] = None
    land_holding_acres: Optional[float] = None
    language_preference: str = "en"


class MetadataValidateRequest(BaseModel):
    fields: dict


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Metadata Engine starting...")
    await init_db()
    yield

app = FastAPI(title="AIforBharat Metadata Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="metadata_engine", uptime_seconds=time.time() - START_TIME)


@app.post("/metadata/process", response_model=ApiResponse, tags=["Metadata"])
async def process_user_metadata(data: MetadataProcessRequest):
    """
    Process raw user input into normalized, enriched metadata.
    Derives: age_group, income_bracket, life_stage, tax_bracket,
    employment_category, farmer_category, bpl_status, etc.
    
    Input: Raw user profile fields
    Output: Normalized profile + derived_attributes
    """
    raw_dict = data.model_dump(exclude_none=True)
    processed = process_metadata(raw_dict)

    # Cache the processed metadata
    metadata_cache.set(f"user:{data.user_id}", processed)

    await event_bus.publish(EventMessage(
        event_type=EventType.METADATA_CREATED,
        source_engine="metadata_engine",
        user_id=data.user_id,
        payload={"derived_attributes": processed.get("derived_attributes", {})},
    ))

    return ApiResponse(message="Metadata processed", data=processed)


@app.get("/metadata/user/{user_id}", response_model=ApiResponse, tags=["Metadata"])
async def get_user_metadata(user_id: str):
    """Get processed metadata for a user from cache."""
    cached = metadata_cache.get(f"user:{user_id}")
    if not cached:
        raise HTTPException(status_code=404, detail="Metadata not found. Process user data first.")
    return ApiResponse(data=cached)


@app.post("/metadata/validate", response_model=ApiResponse, tags=["Metadata"])
async def validate_fields(data: MetadataValidateRequest):
    """
    Validate individual fields without processing.
    Returns validation results per field.
    """
    results = {}
    for field, value in data.fields.items():
        if field == "state":
            results[field] = {
                "valid": value.strip().title() in INDIAN_STATES or normalize_state_name(value) in INDIAN_STATES,
                "normalized": normalize_state_name(value),
            }
        elif field == "pincode":
            results[field] = {
                "valid": value.isdigit() and len(value) == 6,
                "normalized": value.strip()[:6],
            }
        elif field == "phone":
            results[field] = {
                "valid": value.isdigit() and len(value) == 10 and value[0] in "6789",
            }
        elif field == "annual_income":
            try:
                income = float(value)
                results[field] = {
                    "valid": income >= 0,
                    "income_bracket": get_income_bracket(income) if income >= 0 else None,
                }
            except ValueError:
                results[field] = {"valid": False}
        else:
            results[field] = {"valid": True, "normalized": str(value).strip()}

    return ApiResponse(data={"validations": results})


@app.get("/metadata/schemas", response_model=ApiResponse, tags=["Metadata"])
async def get_schemas():
    """Get the current metadata schema definition."""
    return ApiResponse(data={
        "version": "1.0",
        "fields": {
            "user_id": {"type": "string", "required": True},
            "name": {"type": "string", "max_length": 255},
            "phone": {"type": "string", "pattern": "^[6-9]\\d{9}$"},
            "email": {"type": "string", "format": "email"},
            "date_of_birth": {"type": "string", "format": "YYYY-MM-DD"},
            "gender": {"type": "string", "enum": ["male", "female", "other"]},
            "state": {"type": "string", "enum": "INDIAN_STATES"},
            "district": {"type": "string"},
            "pincode": {"type": "string", "pattern": "^\\d{6}$"},
            "annual_income": {"type": "number", "min": 0},
            "occupation": {"type": "string"},
            "category": {"type": "string", "enum": ["General", "SC", "ST", "OBC", "EWS"]},
            "marital_status": {"type": "string", "enum": ["single", "married", "divorced", "widowed"]},
            "education_level": {"type": "string"},
            "family_size": {"type": "integer", "min": 1},
            "is_bpl": {"type": "boolean"},
            "is_rural": {"type": "boolean"},
            "land_holding_acres": {"type": "number", "min": 0},
        },
        "derived_attributes": [
            "age", "age_group", "is_minor", "is_senior_citizen",
            "income_bracket", "tax_bracket", "is_bpl",
            "life_stage", "employment_category",
            "is_sc_st", "is_obc", "is_ews",
            "area_type", "farmer_category",
        ],
    })
