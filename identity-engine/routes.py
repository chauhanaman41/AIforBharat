"""
Identity Engine — API Routes
==============================
CRUD operations on encrypted identity vault.
"""

import logging
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_async_session
from shared.models import ApiResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.utils import generate_id, sha256_hash

from .models import IdentityVault, encrypt_field, decrypt_field

logger = logging.getLogger("identity_engine.routes")
identity_router = APIRouter(tags=["Identity"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateIdentityRequest(BaseModel):
    user_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    dob: Optional[str] = None
    aadhaar: Optional[str] = None  # Will be hashed, never stored plain
    pan: Optional[str] = None      # Will be hashed, never stored plain


class UpdateRolesRequest(BaseModel):
    roles: list[str]


class DelegationRequest(BaseModel):
    delegate_token: str
    permissions: list[str]
    expires_at: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@identity_router.post("/create", response_model=ApiResponse)
async def create_identity(data: CreateIdentityRequest, session: AsyncSession = Depends(get_async_session)):
    """
    Create a new identity vault entry.
    PII is encrypted with AES-256-GCM before storage.
    Returns an opaque identity_token for inter-engine use.
    
    Input: {user_id, name?, phone?, email?, address?, dob?, aadhaar?, pan?}
    Output: {identity_token, user_id}
    """
    # Check if identity already exists for this user
    result = await session.execute(select(IdentityVault).where(IdentityVault.user_id == data.user_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Identity already exists for this user")

    identity_token = secrets.token_hex(32)  # 64-char opaque token

    vault = IdentityVault(
        identity_token=identity_token,
        user_id=data.user_id,
        encrypted_name=encrypt_field(data.name) if data.name else None,
        encrypted_phone=encrypt_field(data.phone) if data.phone else None,
        encrypted_email=encrypt_field(data.email) if data.email else None,
        encrypted_address=encrypt_field(data.address) if data.address else None,
        encrypted_dob=encrypt_field(data.dob) if data.dob else None,
        aadhaar_hash=sha256_hash(data.aadhaar) if data.aadhaar else None,
        pan_hash=sha256_hash(data.pan) if data.pan else None,
    )
    session.add(vault)
    await session.commit()

    await event_bus.publish(EventMessage(
        event_type=EventType.IDENTITY_CREATED,
        source_engine="identity_engine",
        user_id=data.user_id,
        payload={"identity_token": identity_token},
    ))

    logger.info(f"Identity created for user {data.user_id}")

    return ApiResponse(
        message="Identity vault created",
        data={"identity_token": identity_token, "user_id": data.user_id},
    )


@identity_router.get("/{token}", response_model=ApiResponse)
async def get_identity(token: str, session: AsyncSession = Depends(get_async_session)):
    """
    Retrieve decrypted identity by token.
    
    Input: identity_token in URL
    Output: Decrypted PII fields
    """
    result = await session.execute(
        select(IdentityVault).where(IdentityVault.identity_token == token, IdentityVault.is_deleted == False)
    )
    vault = result.scalar_one_or_none()
    if not vault:
        raise HTTPException(status_code=404, detail="Identity not found")

    return ApiResponse(data={
        "identity_token": vault.identity_token,
        "user_id": vault.user_id,
        "name": decrypt_field(vault.encrypted_name) if vault.encrypted_name else None,
        "phone": decrypt_field(vault.encrypted_phone) if vault.encrypted_phone else None,
        "email": decrypt_field(vault.encrypted_email) if vault.encrypted_email else None,
        "address": decrypt_field(vault.encrypted_address) if vault.encrypted_address else None,
        "dob": decrypt_field(vault.encrypted_dob) if vault.encrypted_dob else None,
        "roles": vault.roles,
        "identity_verified": vault.identity_verified,
        "verification_level": vault.verification_level,
        "created_at": vault.created_at.isoformat(),
    })


@identity_router.get("/{token}/profile", response_model=ApiResponse)
async def get_identity_profile(token: str, session: AsyncSession = Depends(get_async_session)):
    """Get a minimal profile view (non-sensitive fields only)."""
    result = await session.execute(
        select(IdentityVault).where(IdentityVault.identity_token == token, IdentityVault.is_deleted == False)
    )
    vault = result.scalar_one_or_none()
    if not vault:
        raise HTTPException(status_code=404, detail="Identity not found")

    return ApiResponse(data={
        "identity_token": vault.identity_token,
        "roles": vault.roles,
        "identity_verified": vault.identity_verified,
        "verification_level": vault.verification_level,
        "has_aadhaar": vault.aadhaar_hash is not None,
        "has_pan": vault.pan_hash is not None,
    })


@identity_router.put("/{token}/roles", response_model=ApiResponse)
async def update_roles(token: str, data: UpdateRolesRequest, session: AsyncSession = Depends(get_async_session)):
    """
    Update identity roles (citizen, farmer, business, guardian, admin).
    
    Input: {roles: ["citizen", "farmer"]}
    Output: {updated_roles}
    """
    result = await session.execute(
        select(IdentityVault).where(IdentityVault.identity_token == token, IdentityVault.is_deleted == False)
    )
    vault = result.scalar_one_or_none()
    if not vault:
        raise HTTPException(status_code=404, detail="Identity not found")

    valid_roles = {"citizen", "farmer", "business", "guardian", "admin"}
    for role in data.roles:
        if role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    vault.roles = data.roles
    vault.updated_at = datetime.utcnow()
    await session.commit()

    await event_bus.publish(EventMessage(
        event_type=EventType.ROLE_UPDATED,
        source_engine="identity_engine",
        user_id=vault.user_id,
        payload={"roles": data.roles},
    ))

    return ApiResponse(message="Roles updated", data={"roles": data.roles})


@identity_router.post("/{token}/export", response_model=ApiResponse)
async def export_identity(token: str, session: AsyncSession = Depends(get_async_session)):
    """
    Data portability export — DPDP Act compliance.
    Returns all user data in portable JSON format.
    """
    result = await session.execute(
        select(IdentityVault).where(IdentityVault.identity_token == token, IdentityVault.is_deleted == False)
    )
    vault = result.scalar_one_or_none()
    if not vault:
        raise HTTPException(status_code=404, detail="Identity not found")

    export_data = {
        "export_type": "identity_data_export",
        "export_timestamp": datetime.utcnow().isoformat(),
        "user_id": vault.user_id,
        "identity_token": vault.identity_token,
        "personal_data": {
            "name": decrypt_field(vault.encrypted_name) if vault.encrypted_name else None,
            "phone": decrypt_field(vault.encrypted_phone) if vault.encrypted_phone else None,
            "email": decrypt_field(vault.encrypted_email) if vault.encrypted_email else None,
            "address": decrypt_field(vault.encrypted_address) if vault.encrypted_address else None,
            "dob": decrypt_field(vault.encrypted_dob) if vault.encrypted_dob else None,
        },
        "roles": vault.roles,
        "verification": {
            "verified": vault.identity_verified,
            "level": vault.verification_level,
        },
        "created_at": vault.created_at.isoformat(),
    }

    await event_bus.publish(EventMessage(
        event_type=EventType.DATA_EXPORTED,
        source_engine="identity_engine",
        user_id=vault.user_id,
    ))

    return ApiResponse(message="Data export generated", data=export_data)


@identity_router.delete("/{token}", response_model=ApiResponse)
async def delete_identity(token: str, session: AsyncSession = Depends(get_async_session)):
    """
    Cryptographic deletion — right to forget (DPDP Act).
    Destroys encrypted data by overwriting with random bytes,
    effectively making the encryption key irrelevant.
    """
    result = await session.execute(
        select(IdentityVault).where(IdentityVault.identity_token == token)
    )
    vault = result.scalar_one_or_none()
    if not vault:
        raise HTTPException(status_code=404, detail="Identity not found")

    # Cryptographic deletion: overwrite encrypted fields with random data
    vault.encrypted_name = secrets.token_hex(32)
    vault.encrypted_phone = secrets.token_hex(16)
    vault.encrypted_email = secrets.token_hex(32)
    vault.encrypted_address = secrets.token_hex(64)
    vault.encrypted_dob = secrets.token_hex(8)
    vault.aadhaar_hash = None
    vault.pan_hash = None
    vault.is_deleted = True
    vault.updated_at = datetime.utcnow()

    await session.commit()

    await event_bus.publish(EventMessage(
        event_type=EventType.IDENTITY_DELETED,
        source_engine="identity_engine",
        user_id=vault.user_id,
    ))

    logger.info(f"Identity cryptographically deleted for user {vault.user_id}")

    return ApiResponse(message="Identity deleted (cryptographic deletion)")
