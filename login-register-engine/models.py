"""
Login/Register Engine — Database Models
=========================================
SQLAlchemy ORM models for users and sessions.
"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Float, Text, JSON
from shared.database import Base


class User(Base):
    """User account table — core identity for authentication."""
    __tablename__ = "users"

    id = Column(String(50), primary_key=True)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    date_of_birth = Column(String(10), nullable=True)
    gender = Column(String(20), nullable=True)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    language_preference = Column(String(5), default="en")
    roles = Column(JSON, default=["citizen"])

    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Consent
    consent_data_processing = Column(Boolean, default=False)
    consent_timestamp = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


class OTPRecord(Base):
    """OTP verification records."""
    __tablename__ = "otp_records"

    id = Column(String(50), primary_key=True)
    phone = Column(String(15), nullable=False, index=True)
    otp_code = Column(String(6), nullable=False)
    purpose = Column(String(20), default="login")  # login, register, reset
    is_used = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RefreshToken(Base):
    """Active refresh tokens for session management."""
    __tablename__ = "refresh_tokens"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True)
    device_info = Column(String(255), nullable=True)
    is_revoked = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
