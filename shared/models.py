"""
AIforBharat — Shared Data Models
=================================
Pydantic models used across multiple engines for type safety and consistency.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    CITIZEN = "citizen"
    FARMER = "farmer"
    BUSINESS = "business"
    GUARDIAN = "guardian"
    ADMIN = "admin"


class EventType(str, Enum):
    # Auth events
    USER_REGISTERED = "USER_REGISTERED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    TOKEN_REFRESHED = "TOKEN_REFRESHED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    LOGOUT = "LOGOUT"

    # Identity events
    IDENTITY_CREATED = "IDENTITY_CREATED"
    IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
    IDENTITY_DELETED = "IDENTITY_DELETED"
    ROLE_UPDATED = "ROLE_UPDATED"
    DATA_EXPORTED = "DATA_EXPORTED"

    # Metadata events
    METADATA_CREATED = "METADATA_CREATED"
    METADATA_UPDATED = "METADATA_UPDATED"
    METADATA_CONFLICT = "METADATA_CONFLICT"
    PROFILE_UPDATED = "PROFILE_UPDATED"

    # Policy events
    POLICY_FETCHED = "POLICY_FETCHED"
    POLICY_UPDATED = "POLICY_UPDATED"
    POLICY_AMENDED = "POLICY_AMENDED"
    POLICY_REPEALED = "POLICY_REPEALED"

    # Document events
    DOCUMENT_PROCESSED = "DOCUMENT_PROCESSED"
    DOCUMENT_VERIFIED = "DOCUMENT_VERIFIED"
    DOCUMENT_FETCHED = "DOCUMENT_FETCHED"
    DOCUMENT_UPDATED = "DOCUMENT_UPDATED"
    DOCUMENT_PARSED = "DOCUMENT_PARSED"

    # Chunk events
    CHUNKS_CREATED = "CHUNKS_CREATED"

    # Eligibility events
    ELIGIBILITY_COMPUTED = "ELIGIBILITY_COMPUTED"
    ELIGIBILITY_CHECKED = "ELIGIBILITY_CHECKED"
    ELIGIBILITY_CACHE_INVALIDATED = "ELIGIBILITY_CACHE_INVALIDATED"

    # Deadline events
    DEADLINE_CREATED = "DEADLINE_CREATED"
    DEADLINE_ESCALATED = "DEADLINE_ESCALATED"
    DEADLINE_COMPLETED = "DEADLINE_COMPLETED"
    DEADLINE_APPROACHING = "DEADLINE_APPROACHING"

    # AI events
    AI_RESPONSE_GENERATED = "AI_RESPONSE_GENERATED"
    AI_QUERY_PROCESSED = "AI_QUERY_PROCESSED"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    TRUST_SCORE_COMPUTED = "TRUST_SCORE_COMPUTED"
    TRUST_SCORE_UPDATED = "TRUST_SCORE_UPDATED"

    # Simulation events
    SIMULATION_COMPLETED = "SIMULATION_COMPLETED"
    SIMULATION_RUN = "SIMULATION_RUN"

    # Profile events
    PROFILE_GENERATED = "PROFILE_GENERATED"

    # Data store events
    RAW_DATA_STORED = "RAW_DATA_STORED"
    INTEGRITY_VIOLATION = "INTEGRITY_VIOLATION"
    METADATA_STORED = "METADATA_STORED"

    # Sync events
    GOV_DATA_SYNCED = "GOV_DATA_SYNCED"
    BUDGET_REALLOCATED = "BUDGET_REALLOCATED"

    # Generic
    SYSTEM_ERROR = "SYSTEM_ERROR"
    HEALTH_CHECK = "HEALTH_CHECK"


class EligibilityVerdict(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


class DeadlinePriority(str, Enum):
    INFO = "info"
    IMPORTANT = "important"
    URGENT = "urgent"
    CRITICAL = "critical"
    OVERDUE = "overdue"


class TrustLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnomalyScore(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    BLOCK = "block"


# ── Core Models ───────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    """Detailed error information for the frontend."""
    code: str = Field(..., description="Machine-readable error code (e.g., VECTOR_TIMEOUT)")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Optional technical details or stack trace")
    attr: Optional[str] = Field(None, description="The attribute that caused the error (for validation errors)")


# ── Standardized Error Codes ──────────────────────────────────────────────────

class ErrorCode:
    """Machine-readable error codes returned to the frontend."""
    # Infrastructure
    VECTOR_TIMEOUT = "VECTOR_TIMEOUT"           # Retrieval service too slow
    NIM_FAILURE = "NIM_FAILURE"                 # AI inference service down
    ENGINE_UNAVAILABLE = "ENGINE_UNAVAILABLE"   # Downstream engine not responding
    ENGINE_TIMEOUT = "ENGINE_TIMEOUT"           # Downstream engine timed out
    CIRCUIT_OPEN = "CIRCUIT_OPEN"               # Circuit breaker tripped

    # Auth
    AUTH_EXPIRED = "AUTH_EXPIRED"               # JWT token expired
    AUTH_INVALID = "AUTH_INVALID"               # JWT token malformed / invalid
    AUTH_REQUIRED = "AUTH_REQUIRED"             # No token provided

    # Rate limiting
    RATE_LIMIT = "RATE_LIMIT"                   # Too many requests
    BURST_LIMIT = "BURST_LIMIT"                 # Per-second burst exceeded

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"       # Request body validation failed
    NOT_FOUND = "NOT_FOUND"                     # Resource not found

    # Internal
    INTERNAL_ERROR = "INTERNAL_ERROR"           # Unhandled server error
    PARTIAL_FAILURE = "PARTIAL_FAILURE"         # Some pipeline steps degraded


def make_error(code: str, message: str, detail: str = None, attr: str = None) -> ErrorDetail:
    """Factory helper to construct an ErrorDetail."""
    return ErrorDetail(code=code, message=message, detail=detail, attr=attr)


class ApiResponse(BaseModel):
    """Standard API response wrapper used by all engines."""
    success: bool = True
    message: str = "OK"
    data: Any = None
    errors: Optional[list[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: Optional[str] = Field(default=None, description="X-Trace-ID for end-to-end request tracing")


class PaginatedResponse(BaseModel):
    """Paginated response for list endpoints."""
    data: list[Any] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    has_next: bool = False


class HealthResponse(BaseModel):
    """Health check response."""
    engine: str
    status: str = "healthy"
    version: str = "1.0.0"
    uptime_seconds: float = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: dict[str, str] = {}


class EventMessage(BaseModel):
    """Event bus message format for inter-engine communication."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    source_engine: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    payload: dict[str, Any] = {}
    correlation_id: Optional[str] = None


class UserProfile(BaseModel):
    """Core user profile shared across engines."""
    user_id: str
    identity_token: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    pincode: Optional[str] = None
    annual_income: Optional[float] = None
    occupation: Optional[str] = None
    category: Optional[str] = None  # General, SC, ST, OBC
    religion: Optional[str] = None
    marital_status: Optional[str] = None
    education_level: Optional[str] = None
    family_size: Optional[int] = None
    is_bpl: Optional[bool] = None
    is_rural: Optional[bool] = None
    disability_status: Optional[str] = None
    land_holding_acres: Optional[float] = None
    language_preference: str = "en"
    roles: list[UserRole] = [UserRole.CITIZEN]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SchemeInfo(BaseModel):
    """Government scheme information."""
    scheme_id: str
    name: str
    description: Optional[str] = None
    ministry: Optional[str] = None
    department: Optional[str] = None
    state: Optional[str] = None  # None = central scheme
    category: Optional[str] = None
    benefit_type: Optional[str] = None
    benefit_amount: Optional[str] = None
    application_url: Optional[str] = None
    deadline: Optional[str] = None
    documents_required: list[str] = []
    eligibility_summary: Optional[str] = None
    source_url: Optional[str] = None
    version: int = 1
    effective_from: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class TrustScore(BaseModel):
    """Trust score for any platform output."""
    composite_score: float = Field(ge=0.0, le=1.0)
    data_quality: float = Field(ge=0.0, le=1.0)
    model_confidence: float = Field(ge=0.0, le=1.0)
    source_authority: float = Field(ge=0.0, le=1.0)
    temporal_freshness: float = Field(ge=0.0, le=1.0)
    level: TrustLevel = TrustLevel.MEDIUM
    provenance: list[dict] = []
    alerts: list[str] = []
