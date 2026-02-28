"""
Identity Engine — Database Models & Encryption
================================================
AES-256-GCM encryption for PII fields, tokenized identity vault.
"""

import base64
import os
import json
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import Column, String, Boolean, DateTime, LargeBinary, JSON, Text
from shared.database import Base
from shared.config import settings


# ── AES-256-GCM Encryption Helpers ───────────────────────────────────────────

def _get_aes_key() -> bytes:
    """Derive a 256-bit AES key from the configured secret."""
    key_hex = settings.AES_ENCRYPTION_KEY
    # Ensure 32 bytes for AES-256
    key_bytes = bytes.fromhex(key_hex)
    if len(key_bytes) < 32:
        key_bytes = key_bytes + b'\x00' * (32 - len(key_bytes))
    return key_bytes[:32]


def encrypt_field(plaintext: str) -> str:
    """
    Encrypt a string using AES-256-GCM.
    Returns base64-encoded nonce+ciphertext.
    """
    if not plaintext:
        return ""
    key = _get_aes_key()
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    # Encode nonce + ciphertext as base64
    return base64.b64encode(nonce + ciphertext).decode('utf-8')


def decrypt_field(encrypted: str) -> str:
    """
    Decrypt an AES-256-GCM encrypted field.
    Expects base64-encoded nonce+ciphertext.
    """
    if not encrypted:
        return ""
    key = _get_aes_key()
    raw = base64.b64decode(encrypted)
    nonce = raw[:12]
    ciphertext = raw[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode('utf-8')


# ── ORM Model ────────────────────────────────────────────────────────────────

class IdentityVault(Base):
    """
    Encrypted identity vault.
    All PII fields are stored as AES-256-GCM encrypted base64 strings.
    identity_token is the platform-wide opaque identifier.
    """
    __tablename__ = "identity_vault"

    identity_token = Column(String(64), primary_key=True)  # Platform-unique opaque token
    user_id = Column(String(50), unique=True, nullable=False, index=True)

    # Encrypted PII fields (stored as base64-encoded AES-256-GCM ciphertext)
    encrypted_name = Column(Text, nullable=True)
    encrypted_phone = Column(Text, nullable=True)
    encrypted_email = Column(Text, nullable=True)
    encrypted_address = Column(Text, nullable=True)
    encrypted_dob = Column(Text, nullable=True)

    # Hashed identifiers (for lookup without decryption)
    aadhaar_hash = Column(String(64), nullable=True, index=True)  # SHA-256 of Aadhaar
    pan_hash = Column(String(64), nullable=True, index=True)      # SHA-256 of PAN

    # Roles & permissions
    roles = Column(JSON, default=["citizen"])
    delegations = Column(JSON, default=[])  # Guardian/delegate relationships

    # Verification status
    identity_verified = Column(Boolean, default=False)
    verification_level = Column(String(20), default="basic")  # basic, aadhaar, digilocker

    # Metadata
    encryption_key_version = Column(String(10), default="v1")
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
