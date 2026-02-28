"""
AIforBharat — Shared Utilities
================================
Common helper functions used across all engines.
"""

import hashlib
import logging
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

import jwt
from shared.config import settings

logger = logging.getLogger("utils")


# ── Unique ID Generation ─────────────────────────────────────────────────────

def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix. E.g., 'usr_abc123'."""
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}_{uid}" if prefix else uid


def generate_uuid() -> str:
    """Generate a full UUID4 string."""
    return str(uuid.uuid4())


# ── Hashing ───────────────────────────────────────────────────────────────────

def sha256_hash(data: str) -> str:
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hash_chain(current_hash: str, previous_hash: str) -> str:
    """Compute a hash chain link: SHA-256(current + previous)."""
    return sha256_hash(f"{current_hash}{previous_hash}")


# ── JWT Helpers ───────────────────────────────────────────────────────────────

def create_access_token(user_id: str, roles: list[str] = None, extra: dict = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: Subject (user identifier).
        roles: List of user roles.
        extra: Additional claims to include.
    
    Returns:
        Encoded JWT string.
    """
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "roles": roles or ["citizen"],
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create a JWT refresh token with longer expiry."""
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    
    Returns:
        Decoded payload dict.
    
    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidTokenError: Token is invalid.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ── Date/Time Helpers ─────────────────────────────────────────────────────────

def utcnow() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()


def days_until(target_date: datetime) -> int:
    """Calculate days remaining until a target date."""
    delta = target_date - datetime.utcnow()
    return max(0, delta.days)


def format_indian_currency(amount: float) -> str:
    """Format a number as Indian currency (₹)."""
    if amount >= 1_00_00_000:
        return f"₹{amount / 1_00_00_000:.2f} Cr"
    elif amount >= 1_00_000:
        return f"₹{amount / 1_00_000:.2f} L"
    elif amount >= 1_000:
        return f"₹{amount / 1_000:.2f}K"
    return f"₹{amount:.2f}"


# ── Performance Helpers ───────────────────────────────────────────────────────

def timer(func):
    """Decorator to measure function execution time."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"{func.__name__} completed in {elapsed:.2f}ms")
        return result

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"{func.__name__} completed in {elapsed:.2f}ms")
        return result

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# ── Indian Data Helpers ───────────────────────────────────────────────────────

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]

INDIAN_LANGUAGES = [
    "as", "bn", "bodo", "doi", "en", "gu", "hi", "kn", "ks", "kok",
    "mai", "ml", "mni", "mr", "ne", "or", "pa", "sa", "sat", "sd",
    "ta", "te", "ur",
]


def normalize_state_name(state: str) -> str:
    """Normalize an Indian state name to the canonical form."""
    state_lower = state.strip().lower()
    for s in INDIAN_STATES:
        if s.lower() == state_lower:
            return s
    # Try partial match
    for s in INDIAN_STATES:
        if state_lower in s.lower() or s.lower() in state_lower:
            return s
    return state.strip().title()


def get_age_group(age: int) -> str:
    """Derive age group from age."""
    if age < 18:
        return "minor"
    elif age < 25:
        return "youth"
    elif age < 40:
        return "young_adult"
    elif age < 60:
        return "middle_aged"
    else:
        return "senior_citizen"


def get_income_bracket(annual_income: float) -> str:
    """Derive income bracket from annual income in INR."""
    if annual_income <= 2_50_000:
        return "below_2.5L"
    elif annual_income <= 5_00_000:
        return "2.5L_to_5L"
    elif annual_income <= 7_50_000:
        return "5L_to_7.5L"
    elif annual_income <= 10_00_000:
        return "7.5L_to_10L"
    elif annual_income <= 15_00_000:
        return "10L_to_15L"
    elif annual_income <= 25_00_000:
        return "15L_to_25L"
    else:
        return "above_25L"
