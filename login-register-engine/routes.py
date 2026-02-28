"""
Login/Register Engine — API Routes
=====================================
Handles registration, login, OTP, JWT token lifecycle.
"""

import logging
import random
import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_async_session
from shared.models import ApiResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.utils import (
    generate_id,
    create_access_token,
    create_refresh_token,
    decode_token,
    sha256_hash,
)

from .models import User, OTPRecord, RefreshToken

logger = logging.getLogger("login_register.routes")
auth_router = APIRouter(tags=["Auth"])


# ── Request/Response Schemas ──────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    phone: str = Field(..., pattern=r"^[6-9]\d{9}$", description="10-digit Indian mobile number")
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    state: Optional[str] = None
    district: Optional[str] = None
    language_preference: str = "en"
    consent_data_processing: bool = True

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if len(v) != 10:
            raise ValueError("Phone must be exactly 10 digits")
        return v


class LoginRequest(BaseModel):
    phone: str = Field(..., pattern=r"^[6-9]\d{9}$")
    password: str = Field(..., min_length=1)


class OTPSendRequest(BaseModel):
    phone: str = Field(..., pattern=r"^[6-9]\d{9}$")
    purpose: str = "login"


class OTPVerifyRequest(BaseModel):
    phone: str = Field(..., pattern=r"^[6-9]\d{9}$")
    otp_code: str = Field(..., pattern=r"^\d{6}$")


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    pincode: Optional[str] = None
    language_preference: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    refresh_token: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash password using bcrypt with 12 rounds."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


async def get_user_by_phone(session: AsyncSession, phone: str) -> Optional[User]:
    """Look up a user by phone number."""
    result = await session.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: str) -> Optional[User]:
    """Look up a user by ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_current_user_dep(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Dependency: extract and validate JWT, return User object."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
        payload = decode_token(token)
        user = await get_user_by_id(session, payload["sub"])
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@auth_router.post("/register", response_model=ApiResponse)
async def register(data: RegisterRequest, session: AsyncSession = Depends(get_async_session)):
    """
    Register a new user account.
    
    Input:
        {phone, password, name, state?, district?, language_preference?, consent_data_processing}
    
    Output:
        {user_id, phone, name, access_token, refresh_token}
    """
    # Check if phone already exists
    existing = await get_user_by_phone(session, data.phone)
    if existing:
        raise HTTPException(status_code=409, detail="Phone number already registered")

    # Create user
    user_id = generate_id("usr")
    user = User(
        id=user_id,
        phone=data.phone,
        password_hash=hash_password(data.password),
        name=data.name,
        state=data.state,
        district=data.district,
        language_preference=data.language_preference,
        consent_data_processing=data.consent_data_processing,
        consent_timestamp=datetime.utcnow() if data.consent_data_processing else None,
        roles=["citizen"],
    )
    session.add(user)

    # Generate tokens
    access_token = create_access_token(user_id, roles=["citizen"])
    refresh_tok = create_refresh_token(user_id)

    # Store refresh token
    rt = RefreshToken(
        id=generate_id("rt"),
        user_id=user_id,
        token_hash=sha256_hash(refresh_tok),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    session.add(rt)
    await session.commit()

    # Publish event
    await event_bus.publish(EventMessage(
        event_type=EventType.USER_REGISTERED,
        source_engine="login_register",
        user_id=user_id,
        payload={"phone": data.phone, "name": data.name, "state": data.state},
    ))

    logger.info(f"User registered: {user_id} ({data.phone})")

    return ApiResponse(
        message="Registration successful",
        data={
            "user_id": user_id,
            "phone": data.phone,
            "name": data.name,
            "access_token": access_token,
            "refresh_token": refresh_tok,
            "token_type": "bearer",
        },
    )


@auth_router.post("/login", response_model=ApiResponse)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_async_session)):
    """
    Login with phone number and password.
    
    Input: {phone, password}
    Output: {user_id, access_token, refresh_token}
    """
    user = await get_user_by_phone(session, data.phone)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid phone or password")

    # Check account lock
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=423,
            detail=f"Account locked until {user.locked_until.isoformat()}",
        )

    # Verify password
    if not verify_password(data.password, user.password_hash):
        user.failed_login_attempts += 1
        # Lock after 5 failed attempts for 15 minutes
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            await event_bus.publish(EventMessage(
                event_type=EventType.ACCOUNT_LOCKED,
                source_engine="login_register",
                user_id=user.id,
                payload={"reason": "too_many_failed_attempts"},
            ))
        await session.commit()

        await event_bus.publish(EventMessage(
            event_type=EventType.LOGIN_FAILED,
            source_engine="login_register",
            user_id=user.id,
            payload={"phone": data.phone},
        ))
        raise HTTPException(status_code=401, detail="Invalid phone or password")

    # Successful login — reset counters
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()

    # Generate tokens
    access_token = create_access_token(
        user.id,
        roles=user.roles if isinstance(user.roles, list) else ["citizen"],
        extra={"state": user.state},
    )
    refresh_tok = create_refresh_token(user.id)

    rt = RefreshToken(
        id=generate_id("rt"),
        user_id=user.id,
        token_hash=sha256_hash(refresh_tok),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    session.add(rt)
    await session.commit()

    await event_bus.publish(EventMessage(
        event_type=EventType.LOGIN_SUCCESS,
        source_engine="login_register",
        user_id=user.id,
        payload={"phone": data.phone},
    ))

    logger.info(f"User logged in: {user.id}")

    return ApiResponse(
        message="Login successful",
        data={
            "user_id": user.id,
            "name": user.name,
            "access_token": access_token,
            "refresh_token": refresh_tok,
            "token_type": "bearer",
        },
    )


@auth_router.post("/otp/send", response_model=ApiResponse)
async def send_otp(data: OTPSendRequest, session: AsyncSession = Depends(get_async_session)):
    """
    Send OTP to phone number. LOCAL MODE: OTP is logged, not actually sent via SMS.
    
    Input: {phone, purpose}
    Output: {message, otp_id} (and OTP logged to console)
    """
    # Generate 6-digit OTP
    otp_code = f"{random.randint(100000, 999999)}"

    otp_record = OTPRecord(
        id=generate_id("otp"),
        phone=data.phone,
        otp_code=otp_code,
        purpose=data.purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    session.add(otp_record)
    await session.commit()

    # LOCAL MODE: Log OTP instead of sending SMS
    logger.info(f"📱 OTP for {data.phone}: {otp_code} (purpose: {data.purpose}) [LOCAL MODE - NOT SENT VIA SMS]")

    return ApiResponse(
        message="OTP sent successfully (local mode: check logs)",
        data={
            "otp_id": otp_record.id,
            "phone": data.phone,
            "expires_in_seconds": 600,
            "debug_otp": otp_code,  # Only in local/debug mode
        },
    )


@auth_router.post("/otp/verify", response_model=ApiResponse)
async def verify_otp(data: OTPVerifyRequest, session: AsyncSession = Depends(get_async_session)):
    """
    Verify an OTP code.
    
    Input: {phone, otp_code}
    Output: {verified: true/false}
    """
    # Find latest unused OTP for this phone
    result = await session.execute(
        select(OTPRecord)
        .where(
            OTPRecord.phone == data.phone,
            OTPRecord.is_used == False,
            OTPRecord.expires_at > datetime.utcnow(),
        )
        .order_by(OTPRecord.created_at.desc())
        .limit(1)
    )
    otp_record = result.scalar_one_or_none()

    if not otp_record:
        raise HTTPException(status_code=400, detail="No valid OTP found. Request a new one.")

    otp_record.attempts += 1

    if otp_record.attempts > 3:
        otp_record.is_used = True
        await session.commit()
        raise HTTPException(status_code=429, detail="Too many OTP attempts. Request a new one.")

    if otp_record.otp_code != data.otp_code:
        await session.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Mark OTP as used
    otp_record.is_used = True

    # Mark user as verified
    user = await get_user_by_phone(session, data.phone)
    if user:
        user.is_verified = True

    await session.commit()

    return ApiResponse(
        message="OTP verified successfully",
        data={"verified": True, "phone": data.phone},
    )


@auth_router.post("/token/refresh", response_model=ApiResponse)
async def refresh_token(data: TokenRefreshRequest, session: AsyncSession = Depends(get_async_session)):
    """
    Refresh an access token using a valid refresh token.
    
    Input: {refresh_token}
    Output: {access_token, refresh_token}
    """
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Verify refresh token exists and is not revoked
    token_hash = sha256_hash(data.refresh_token)
    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=401, detail="Refresh token revoked or not found")

    # Revoke old token
    rt.is_revoked = True

    # Get user
    user = await get_user_by_id(session, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Issue new tokens
    new_access = create_access_token(user.id, roles=user.roles or ["citizen"])
    new_refresh = create_refresh_token(user.id)

    new_rt = RefreshToken(
        id=generate_id("rt"),
        user_id=user.id,
        token_hash=sha256_hash(new_refresh),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    session.add(new_rt)
    await session.commit()

    await event_bus.publish(EventMessage(
        event_type=EventType.TOKEN_REFRESHED,
        source_engine="login_register",
        user_id=user.id,
    ))

    return ApiResponse(
        message="Token refreshed",
        data={
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        },
    )


@auth_router.post("/logout", response_model=ApiResponse)
async def logout(
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Logout — revoke all refresh tokens for the user.
    
    Input: Bearer token in Authorization header
    Output: {message}
    """
    # Revoke all refresh tokens for this user
    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.is_revoked == False,
        )
    )
    tokens = result.scalars().all()
    for t in tokens:
        t.is_revoked = True

    await session.commit()

    await event_bus.publish(EventMessage(
        event_type=EventType.LOGOUT,
        source_engine="login_register",
        user_id=user.id,
    ))

    logger.info(f"User logged out: {user.id}")
    return ApiResponse(message="Logged out successfully")


@auth_router.get("/me", response_model=ApiResponse)
async def get_me(user: User = Depends(get_current_user_dep)):
    """
    Get current authenticated user profile.
    
    Input: Bearer token in Authorization header
    Output: {user_id, phone, name, email, state, district, ...}
    """
    return ApiResponse(
        data={
            "user_id": user.id,
            "phone": user.phone,
            "name": user.name,
            "email": user.email,
            "date_of_birth": user.date_of_birth,
            "gender": user.gender,
            "state": user.state,
            "district": user.district,
            "pincode": user.pincode,
            "language_preference": user.language_preference,
            "roles": user.roles,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        },
    )


@auth_router.put("/profile", response_model=ApiResponse)
async def update_profile(
    data: ProfileUpdateRequest,
    user: User = Depends(get_current_user_dep),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Update user profile fields.
    
    Input: {name?, email?, date_of_birth?, gender?, state?, district?, pincode?, language_preference?}
    Output: Updated user profile
    """
    update_fields = data.model_dump(exclude_none=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    for field, value in update_fields.items():
        setattr(user, field, value)

    user.updated_at = datetime.utcnow()
    await session.commit()

    await event_bus.publish(EventMessage(
        event_type=EventType.PROFILE_UPDATED,
        source_engine="login_register",
        user_id=user.id,
        payload={"updated_fields": list(update_fields.keys())},
    ))

    logger.info(f"Profile updated for user {user.id}: {list(update_fields.keys())}")

    return ApiResponse(
        message="Profile updated",
        data={
            "user_id": user.id,
            "updated_fields": list(update_fields.keys()),
        },
    )
