"""
API Gateway — Orchestrator Layer
==================================
Composite routes that chain multiple engines in sequence.
This is the "conductor" that turns 21 independent engines into a
cohesive platform.

Design decisions:
- Lives INSIDE the API Gateway (no new engine).
- Uses httpx async HTTP calls to downstream engines.
- Deterministic controller flows (onboarding, ingestion) use
  hardcoded sequential steps — no LLM decision-making.
- Agent flows (RAG query, voice query) route dynamically
  based on intent classification from Neural Network Engine.
- Every composite flow ends with an audit POST to Raw Data Store.
- Partial failures return degraded responses with a `degraded` list.

Ref: orchestra-formation.md §5 (Orchestrator Design)
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from shared.config import ENGINE_URLS
from shared.models import ApiResponse

from .routes import require_auth

logger = logging.getLogger("api_gateway.orchestrator")

orchestrator_router = APIRouter(prefix="/api/v1", tags=["Orchestrator"])


# ══════════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER — Per-engine failure tracking
# ══════════════════════════════════════════════════════════════════════════════

class CircuitBreaker:
    """
    In-memory circuit breaker per downstream engine.
    States: CLOSED (normal) → OPEN (tripped) → HALF_OPEN (probing).

    - CLOSED: Forward all requests.
    - OPEN: Reject immediately after `failure_threshold` consecutive failures.
    - HALF_OPEN: After `recovery_timeout` seconds, allow 1 probe request.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self._states: dict[str, str] = {}
        self._failure_counts: dict[str, int] = {}
        self._last_failure_time: dict[str, float] = {}
        self._threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

    def _get_state(self, engine: str) -> str:
        state = self._states.get(engine, self.CLOSED)
        if state == self.OPEN:
            last_fail = self._last_failure_time.get(engine, 0)
            if time.time() - last_fail > self._recovery_timeout:
                self._states[engine] = self.HALF_OPEN
                return self.HALF_OPEN
        return state

    def allow_request(self, engine: str) -> bool:
        state = self._get_state(engine)
        if state == self.CLOSED:
            return True
        if state == self.HALF_OPEN:
            return True  # allow probe
        return False  # OPEN → reject

    def record_success(self, engine: str):
        self._failure_counts[engine] = 0
        self._states[engine] = self.CLOSED

    def record_failure(self, engine: str):
        count = self._failure_counts.get(engine, 0) + 1
        self._failure_counts[engine] = count
        self._last_failure_time[engine] = time.time()
        if count >= self._threshold:
            self._states[engine] = self.OPEN
            logger.warning(f"Circuit OPEN for engine '{engine}' after {count} failures")

    def get_status(self) -> dict:
        return {
            engine: {
                "state": self._get_state(engine),
                "failures": self._failure_counts.get(engine, 0),
            }
            for engine in set(list(self._states.keys()) + list(self._failure_counts.keys()))
        }


# Singleton circuit breaker
circuit_breaker = CircuitBreaker()


# ══════════════════════════════════════════════════════════════════════════════
# CALL ENGINE — Core helper for all orchestrator HTTP calls
# ══════════════════════════════════════════════════════════════════════════════

async def call_engine(
    engine_key: str,
    path: str,
    payload: Optional[dict] = None,
    method: str = "POST",
    request_id: str = "",
    timeout: float = 15.0,
) -> dict:
    """
    Call a downstream engine via HTTP. Uses circuit breaker.

    Args:
        engine_key: Key in ENGINE_URLS (e.g. "neural_network")
        path:       Endpoint path (e.g. "/ai/chat")
        payload:    JSON body for POST/PUT
        method:     HTTP method
        request_id: Correlation ID for tracing
        timeout:    Per-call timeout in seconds

    Returns:
        Parsed JSON response body (the 'data' field if wrapped in ApiResponse)

    Raises:
        EngineCallError with engine_key and status info
    """
    base_url = ENGINE_URLS.get(engine_key)
    if not base_url:
        raise EngineCallError(engine_key, 0, f"Unknown engine key: {engine_key}")

    if not circuit_breaker.allow_request(engine_key):
        raise EngineCallError(
            engine_key, 503,
            f"Circuit breaker OPEN for {engine_key}. Engine is temporarily unavailable."
        )

    url = f"{base_url}{path}"
    headers = {
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                json=payload if method in ("POST", "PUT", "PATCH") else None,
                params=payload if method == "GET" and payload else None,
                headers=headers,
            )

        circuit_breaker.record_success(engine_key)

        if response.status_code >= 400:
            body = response.json() if response.content else {}
            raise EngineCallError(engine_key, response.status_code, str(body))

        body = response.json() if response.content else {}

        # Unwrap ApiResponse envelope if present
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body

    except httpx.ConnectError:
        circuit_breaker.record_failure(engine_key)
        raise EngineCallError(engine_key, 503, f"Engine {engine_key} is not responding")
    except httpx.TimeoutException:
        circuit_breaker.record_failure(engine_key)
        raise EngineCallError(engine_key, 504, f"Engine {engine_key} timed out ({timeout}s)")
    except EngineCallError:
        raise
    except Exception as e:
        circuit_breaker.record_failure(engine_key)
        raise EngineCallError(engine_key, 502, str(e))


class EngineCallError(Exception):
    """Raised when a call_engine() call fails."""

    def __init__(self, engine: str, status: int, detail: str):
        self.engine = engine
        self.status = status
        self.detail = detail
        super().__init__(f"[{engine}] {status}: {detail}")


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT HELPER — Posts to Raw Data Store (E3) + Analytics Warehouse (E13)
# ══════════════════════════════════════════════════════════════════════════════

async def audit_log(
    event_type: str,
    user_id: str,
    payload: dict,
    request_id: str = "",
):
    """
    Fire-and-forget audit to E3 (Raw Data Store) and E13 (Analytics).
    Failures are logged but never block the response.
    """
    audit_body = {
        "event_type": event_type,
        "source_engine": "orchestrator",
        "user_id": user_id,
        "payload": payload,
    }
    analytics_body = {
        "event_type": event_type,
        "user_id": user_id,
        "properties": payload,
    }

    async def _post_audit():
        try:
            await call_engine("raw_data_store", "/raw-data/events", audit_body, request_id=request_id)
        except Exception as e:
            logger.warning(f"Audit log to E3 failed (non-blocking): {e}")
        try:
            await call_engine("analytics_warehouse", "/analytics/event", analytics_body, request_id=request_id)
        except Exception as e:
            logger.warning(f"Analytics event to E13 failed (non-blocking): {e}")

    # Schedule as background task — don't await
    asyncio.create_task(_post_audit())


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    message: str
    user_id: str
    session_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=50)


class OnboardRequest(BaseModel):
    phone: str
    password: str
    name: str
    state: Optional[str] = None
    district: Optional[str] = None
    language_preference: str = "en"
    consent_data_processing: bool = True
    # Optional extra profile fields for enrichment
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
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


class IngestPolicyRequest(BaseModel):
    source_url: str
    source_type: str = "web"
    tags: Optional[list[str]] = None


class VoiceQueryRequest(BaseModel):
    text: str
    language: str = "hindi"
    user_id: Optional[str] = None


class EligibilityRequest(BaseModel):
    user_id: str
    profile: dict
    scheme_ids: Optional[list[str]] = None
    explain: bool = True


class SimulateRequest(BaseModel):
    user_id: str
    current_profile: dict
    changes: dict
    explain: bool = True


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSITE ROUTE 1 — RAG Query (Agent Flow)
# ══════════════════════════════════════════════════════════════════════════════
# Pipeline: Intent(E7) → Vector Search(E6) → RAG(E7) → Anomaly(E8) ∥ Trust(E19) → Audit(E3+E13)

@orchestrator_router.post("/query", response_model=ApiResponse)
async def orchestrated_query(body: QueryRequest, request: Request, user=Depends(require_auth)):
    """
    Full RAG query pipeline. Chains intent classification, vector search,
    grounded generation, anomaly check, and trust scoring.

    Ref: orchestra-formation.md §3 Flow A
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    degraded: list[str] = []
    start = time.perf_counter()

    # ── Step 1: Intent Classification (E7) ────────────────────────────────
    intent_data = {"intent": "general", "confidence": 0.0}
    try:
        intent_data = await call_engine(
            "neural_network", "/ai/intent",
            {"message": body.message, "user_id": body.user_id},
            request_id=request_id,
        )
    except EngineCallError as e:
        logger.warning(f"Intent classification failed: {e}")
        degraded.append("intent_classification")

    # ── Step 2: Vector Search (E6) ────────────────────────────────────────
    context_passages: list[str] = []
    vector_results = []
    try:
        vector_data = await call_engine(
            "vector_database", "/vectors/search",
            {"query": body.message, "top_k": body.top_k},
            request_id=request_id,
        )
        vector_results = vector_data.get("results", []) if isinstance(vector_data, dict) else []
        context_passages = [r.get("content", "") for r in vector_results if r.get("content")]
    except EngineCallError as e:
        logger.warning(f"Vector search failed: {e}")
        degraded.append("vector_search")

    # ── Step 3: RAG Generation (E7) ───────────────────────────────────────
    answer_data = {}
    try:
        if context_passages:
            answer_data = await call_engine(
                "neural_network", "/ai/rag",
                {
                    "user_id": body.user_id,
                    "question": body.message,
                    "context_passages": context_passages,
                },
                request_id=request_id,
                timeout=20.0,
            )
        else:
            # Fallback to direct chat if no context passages
            answer_data = await call_engine(
                "neural_network", "/ai/chat",
                {
                    "user_id": body.user_id,
                    "message": body.message,
                    "session_id": body.session_id or str(uuid.uuid4()),
                },
                request_id=request_id,
                timeout=20.0,
            )
    except EngineCallError as e:
        logger.error(f"RAG/Chat generation failed: {e}")
        return ApiResponse(
            success=False,
            message="AI service temporarily unavailable. Please try again.",
            data={"degraded": degraded + ["ai_generation"]},
        )

    # ── Step 4 & 5: Anomaly Check (E8) ∥ Trust Score (E19) — parallel ────
    anomaly_data = {}
    trust_data = {}
    try:
        anomaly_task = call_engine(
            "anomaly_detection", "/anomaly/check",
            {"user_id": body.user_id, "profile": {"response_length": len(str(answer_data))}},
            request_id=request_id,
        )
        trust_task = call_engine(
            "trust_scoring", "/trust/score",
            {
                "user_id": body.user_id,
                "data_sources": [r.get("vector_id", "") for r in vector_results[:3]],
                "model_confidence": intent_data.get("confidence", 0.5),
            },
            request_id=request_id,
        )
        results = await asyncio.gather(anomaly_task, trust_task, return_exceptions=True)

        if isinstance(results[0], Exception):
            logger.warning(f"Anomaly check failed: {results[0]}")
            degraded.append("anomaly_check")
        else:
            anomaly_data = results[0]

        if isinstance(results[1], Exception):
            logger.warning(f"Trust scoring failed: {results[1]}")
            degraded.append("trust_scoring")
        else:
            trust_data = results[1]

    except Exception as e:
        logger.warning(f"Parallel anomaly/trust failed: {e}")
        degraded.extend(["anomaly_check", "trust_scoring"])

    # ── Step 6: Audit log (fire-and-forget) ───────────────────────────────
    await audit_log(
        event_type="RAG_QUERY",
        user_id=body.user_id,
        payload={
            "query": body.message,
            "intent": intent_data.get("intent"),
            "sources_count": len(context_passages),
        },
        request_id=request_id,
    )

    elapsed_ms = (time.perf_counter() - start) * 1000
    return ApiResponse(
        data={
            "response": answer_data.get("answer") or answer_data.get("response", ""),
            "intent": intent_data.get("intent"),
            "intent_confidence": intent_data.get("confidence"),
            "sources": [{"id": r.get("vector_id"), "score": r.get("score"), "content": r.get("content", "")[:200]} for r in vector_results[:5]],
            "anomaly": anomaly_data,
            "trust": trust_data,
            "degraded": degraded if degraded else None,
            "latency_ms": round(elapsed_ms, 1),
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSITE ROUTE 2 — User Onboarding (Controller Flow)
# ══════════════════════════════════════════════════════════════════════════════
# Pipeline: Register(E1) → Identity(E2) → Metadata(E4) → ProcessedMeta(E5)
#           → Eligibility(E15) ∥ Deadlines(E16) → Profile(E12) → Audit(E3+E13)

@orchestrator_router.post("/onboard", response_model=ApiResponse)
async def orchestrated_onboard(body: OnboardRequest, request: Request):
    """
    Full onboarding pipeline. Chains registration, identity creation,
    metadata normalization, eligibility batch check, and profile generation.

    This is a CONTROLLER flow — every step is deterministic and sequential.
    No LLM is invoked.

    Ref: orchestra-formation.md §3 Flow D
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    degraded: list[str] = []

    # ── Step 1: Register (E1) ─────────────────────────────────────────────
    try:
        reg_data = await call_engine(
            "login_register", "/auth/register",
            {
                "phone": body.phone,
                "password": body.password,
                "name": body.name,
                "state": body.state,
                "district": body.district,
                "language_preference": body.language_preference,
                "consent_data_processing": body.consent_data_processing,
            },
            request_id=request_id,
        )
    except EngineCallError as e:
        # Registration is the critical first step — if it fails, bail entirely
        raise HTTPException(status_code=e.status or 500, detail=f"Registration failed: {e.detail}")

    user_id = reg_data.get("user_id", "")
    access_token = reg_data.get("access_token", "")

    # ── Step 2: Create Identity (E2) ──────────────────────────────────────
    identity_token = ""
    try:
        identity_data = await call_engine(
            "identity", "/identity/create",
            {
                "user_id": user_id,
                "name": body.name,
                "phone": body.phone,
                "dob": body.date_of_birth,
            },
            request_id=request_id,
        )
        identity_token = identity_data.get("identity_token", "")
    except EngineCallError as e:
        logger.warning(f"Identity creation failed: {e}")
        degraded.append("identity_creation")

    # ── Step 3: Normalize Metadata (E4) ───────────────────────────────────
    profile_data = {}
    try:
        profile_fields = {
            "user_id": user_id,
            "name": body.name,
            "phone": body.phone,
            "state": body.state,
            "district": body.district,
            "date_of_birth": body.date_of_birth,
            "gender": body.gender,
            "pincode": body.pincode,
            "annual_income": body.annual_income,
            "occupation": body.occupation,
            "category": body.category,
            "religion": body.religion,
            "marital_status": body.marital_status,
            "education_level": body.education_level,
            "family_size": body.family_size,
            "is_bpl": body.is_bpl,
            "is_rural": body.is_rural,
            "disability_status": body.disability_status,
            "land_holding_acres": body.land_holding_acres,
            "language_preference": body.language_preference,
        }
        # Remove None values
        profile_fields = {k: v for k, v in profile_fields.items() if v is not None}

        profile_data = await call_engine(
            "metadata", "/metadata/process",
            profile_fields,
            request_id=request_id,
        )
    except EngineCallError as e:
        logger.warning(f"Metadata normalization failed: {e}")
        degraded.append("metadata_normalization")

    # ── Step 4: Store Processed Metadata (E5) ─────────────────────────────
    try:
        await call_engine(
            "processed_metadata", "/processed-metadata/store",
            {
                "user_id": user_id,
                "processed_data": profile_data.get("normalized", profile_data) if profile_data else {},
                "derived_attributes": profile_data.get("derived_attributes", {}),
            },
            request_id=request_id,
        )
    except EngineCallError as e:
        logger.warning(f"Processed metadata store failed: {e}")
        degraded.append("processed_metadata_store")

    # ── Step 5 & 6: Eligibility(E15) ∥ Deadlines(E16) — parallel ─────────
    eligibility_data = {}
    deadlines_data = {}
    try:
        elig_profile = profile_data.get("normalized", profile_data) if profile_data else {}
        elig_task = call_engine(
            "eligibility_rules", "/eligibility/check",
            {"user_id": user_id, "profile": elig_profile},
            request_id=request_id,
        )
        deadline_task = call_engine(
            "deadline_monitoring", "/deadlines/check",
            {"user_id": user_id, "state": body.state},
            request_id=request_id,
        )
        results = await asyncio.gather(elig_task, deadline_task, return_exceptions=True)

        if isinstance(results[0], Exception):
            logger.warning(f"Eligibility check failed: {results[0]}")
            degraded.append("eligibility_check")
        else:
            eligibility_data = results[0]

        if isinstance(results[1], Exception):
            logger.warning(f"Deadline check failed: {results[1]}")
            degraded.append("deadline_check")
        else:
            deadlines_data = results[1]

    except Exception as e:
        logger.warning(f"Parallel eligibility/deadline failed: {e}")
        degraded.extend(["eligibility_check", "deadline_check"])

    # ── Step 7: Generate Profile (E12) ────────────────────────────────────
    profile_json = {}
    try:
        profile_json = await call_engine(
            "json_user_info", "/profile/generate",
            {
                "user_id": user_id,
                "metadata": profile_data,
                "eligibility": eligibility_data,
                "deadlines": deadlines_data,
            },
            request_id=request_id,
        )
    except EngineCallError as e:
        logger.warning(f"Profile generation failed: {e}")
        degraded.append("profile_generation")

    # ── Step 8: Audit log (fire-and-forget) ───────────────────────────────
    await audit_log(
        event_type="USER_ONBOARDED",
        user_id=user_id,
        payload={
            "phone": body.phone[:4] + "****",  # mask
            "steps_completed": 7 - len(degraded),
            "degraded": degraded,
        },
        request_id=request_id,
    )

    return ApiResponse(
        message="Onboarding complete" if not degraded else "Onboarding complete with some services degraded",
        data={
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": reg_data.get("refresh_token", ""),
            "identity_token": identity_token,
            "eligibility_summary": {
                "eligible": eligibility_data.get("eligible", 0),
                "partial": eligibility_data.get("partial", 0),
                "total_checked": eligibility_data.get("total_schemes_checked", 0),
            } if eligibility_data else None,
            "upcoming_deadlines": deadlines_data.get("total_deadlines", 0) if deadlines_data else None,
            "profile_completeness": profile_json.get("completeness") if profile_json else None,
            "degraded": degraded if degraded else None,
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSITE ROUTE 3 — Eligibility Check with Explanation (Controller Flow)
# ══════════════════════════════════════════════════════════════════════════════
# Pipeline: Eligibility(E15) → optional AI Explanation(E7) → Audit(E3+E13)

@orchestrator_router.post("/check-eligibility", response_model=ApiResponse)
async def orchestrated_eligibility(body: EligibilityRequest, request: Request, user=Depends(require_auth)):
    """
    Eligibility check with optional AI-generated explanation.
    The eligibility verdict is 100% deterministic (E15, boolean logic).
    The explanation is an optional LLM-generated summary (E7).

    Ref: orchestra-formation.md §3 Flow B
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    degraded: list[str] = []

    # ── Step 1: Deterministic Eligibility Check (E15) ─────────────────────
    try:
        elig_data = await call_engine(
            "eligibility_rules", "/eligibility/check",
            {
                "user_id": body.user_id,
                "profile": body.profile,
                "scheme_ids": body.scheme_ids,
            },
            request_id=request_id,
        )
    except EngineCallError as e:
        raise HTTPException(
            status_code=e.status or 500,
            detail=f"Eligibility engine unavailable: {e.detail}",
        )

    # ── Step 2: AI Explanation (E7) — optional, non-blocking ──────────────
    explanation = None
    if body.explain:
        try:
            summary_data = await call_engine(
                "neural_network", "/ai/summarize",
                {
                    "text": f"Eligibility results for user {body.user_id}: "
                            + str(elig_data.get("results", [])),
                    "max_length": 300,
                },
                request_id=request_id,
                timeout=15.0,
            )
            explanation = summary_data.get("summary", "")
        except EngineCallError as e:
            logger.warning(f"AI explanation failed: {e}")
            degraded.append("ai_explanation")

    # ── Step 3: Audit ─────────────────────────────────────────────────────
    await audit_log(
        event_type="ELIGIBILITY_CHECKED",
        user_id=body.user_id,
        payload={
            "eligible": elig_data.get("eligible", 0),
            "partial": elig_data.get("partial", 0),
            "total_checked": elig_data.get("total_schemes_checked", 0),
        },
        request_id=request_id,
    )

    return ApiResponse(
        data={
            **elig_data,
            "explanation": explanation,
            "degraded": degraded if degraded else None,
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSITE ROUTE 4 — Policy Ingestion Pipeline (Controller Flow)
# ══════════════════════════════════════════════════════════════════════════════
# Pipeline: Fetch(E11) → Parse(E21) → Chunk(E10) → Embed(E7) → Vector Upsert(E6)
#           → Tag Metadata(E4) → Audit(E3+E13)

@orchestrator_router.post("/ingest-policy", response_model=ApiResponse)
async def orchestrated_ingest_policy(body: IngestPolicyRequest, request: Request, user=Depends(require_auth)):
    """
    Full policy ingestion pipeline. Fetches a policy document, parses it
    with LLM, chunks the text, generates embeddings, upserts into vector DB,
    and tags metadata.

    Every step is idempotent: hash-based dedup in E11, chunk_id uniqueness in E6.

    Ref: orchestra-formation.md §4 Pipeline 1
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    degraded: list[str] = []
    ingested_docs = []

    # ── Step 1: Fetch Policy (E11) ────────────────────────────────────────
    try:
        fetch_data = await call_engine(
            "policy_fetching", "/schemes/fetch",
            {"source_url": body.source_url, "source_type": body.source_type},
            request_id=request_id,
            timeout=30.0,
        )
    except EngineCallError as e:
        raise HTTPException(
            status_code=e.status or 502,
            detail=f"Policy fetch failed: {e.detail}",
        )

    doc_id = fetch_data.get("document_id") or fetch_data.get("id", str(uuid.uuid4()))
    policy_id = fetch_data.get("policy_id") or fetch_data.get("scheme_id", doc_id)
    raw_text = fetch_data.get("text") or fetch_data.get("content", "")
    title = fetch_data.get("title", body.source_url)

    if not raw_text:
        return ApiResponse(
            success=False,
            message="Fetched document has no text content.",
            data={"document_id": doc_id, "source_url": body.source_url},
        )

    # ── Step 2: Document Understanding (E21) ──────────────────────────────
    parsed_data = {}
    try:
        parsed_data = await call_engine(
            "doc_understanding", "/documents/parse",
            {
                "document_id": doc_id,
                "policy_id": policy_id,
                "title": title,
                "text": raw_text,
            },
            request_id=request_id,
            timeout=25.0,
        )
    except EngineCallError as e:
        logger.warning(f"Document parsing failed: {e}")
        degraded.append("document_parsing")

    # ── Step 3: Chunk Document (E10) ──────────────────────────────────────
    chunks = []
    try:
        chunk_data = await call_engine(
            "chunks", "/chunks/create",
            {
                "document_id": doc_id,
                "policy_id": policy_id,
                "text": raw_text,
                "strategy": "sentence",
                "chunk_size": 512,
                "overlap": 64,
                "metadata": {"title": title, "source_url": body.source_url},
            },
            request_id=request_id,
        )
        chunks = chunk_data.get("chunks", [])
    except EngineCallError as e:
        logger.warning(f"Chunking failed: {e}")
        degraded.append("chunking")

    if not chunks:
        # Can't continue without chunks
        return ApiResponse(
            message="Document fetched but chunking failed. Partial ingestion.",
            data={
                "document_id": doc_id,
                "policy_id": policy_id,
                "parsed": bool(parsed_data),
                "chunks_created": 0,
                "vectors_upserted": 0,
                "degraded": degraded,
            },
        )

    # ── Step 4: Generate Embeddings (E7) ──────────────────────────────────
    embeddings = []
    chunk_texts = [c.get("content", "") for c in chunks]
    try:
        embed_data = await call_engine(
            "neural_network", "/ai/embeddings",
            {"texts": chunk_texts},
            request_id=request_id,
            timeout=20.0,
        )
        embeddings = embed_data.get("embeddings", [])
    except EngineCallError as e:
        logger.warning(f"Embedding generation failed: {e}")
        degraded.append("embedding")

    # ── Step 5: Vector Upsert (E6) ────────────────────────────────────────
    vectors_upserted = 0
    if embeddings and len(embeddings) == len(chunks):
        try:
            vectors_to_upsert = []
            for i, chunk in enumerate(chunks):
                vectors_to_upsert.append({
                    "chunk_id": chunk.get("chunk_id", f"{doc_id}_{i}"),
                    "document_id": doc_id,
                    "policy_id": policy_id,
                    "content": chunk.get("content", ""),
                    "embedding": embeddings[i],
                    "namespace": "policies",
                    "metadata": {
                        "title": title,
                        "chunk_index": i,
                        "source_url": body.source_url,
                    },
                })
            upsert_data = await call_engine(
                "vector_database", "/vectors/upsert/batch",
                {"vectors": vectors_to_upsert},
                request_id=request_id,
            )
            vectors_upserted = upsert_data.get("inserted", len(vectors_to_upsert))
        except EngineCallError as e:
            logger.warning(f"Vector upsert failed: {e}")
            degraded.append("vector_upsert")
    elif embeddings:
        logger.warning(f"Embedding count mismatch: {len(embeddings)} embeddings vs {len(chunks)} chunks")
        degraded.append("embedding_mismatch")

    # ── Step 6: Tag Metadata (E4) — fire-and-forget ───────────────────────
    try:
        await call_engine(
            "metadata", "/metadata/process",
            {
                "user_id": f"policy:{policy_id}",
                "name": title,
                "state": parsed_data.get("state"),
                "occupation": parsed_data.get("scheme_type"),
            },
            request_id=request_id,
        )
    except EngineCallError as e:
        logger.warning(f"Metadata tagging failed (non-critical): {e}")
        degraded.append("metadata_tagging")

    # ── Step 7: Audit ─────────────────────────────────────────────────────
    await audit_log(
        event_type="POLICY_INGESTED",
        user_id="system",
        payload={
            "document_id": doc_id,
            "policy_id": policy_id,
            "title": title,
            "chunks_created": len(chunks),
            "vectors_upserted": vectors_upserted,
            "degraded": degraded,
        },
        request_id=request_id,
    )

    return ApiResponse(
        message="Policy ingestion complete" if not degraded else "Policy ingestion complete with some steps degraded",
        data={
            "document_id": doc_id,
            "policy_id": policy_id,
            "title": title,
            "chunks_created": len(chunks),
            "vectors_upserted": vectors_upserted,
            "parsed_fields": list(parsed_data.keys()) if parsed_data else [],
            "degraded": degraded if degraded else None,
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSITE ROUTE 5 — Voice Query (Agent Flow)
# ══════════════════════════════════════════════════════════════════════════════
# Pipeline: Transcribe(E20) [or use text] → Intent(E7) → Route by intent → Synthesize(E20) → Audit

@orchestrator_router.post("/voice-query", response_model=ApiResponse)
async def orchestrated_voice_query(body: VoiceQueryRequest, request: Request):
    """
    Voice query pipeline. Accepts text (pre-transcribed or typed),
    classifies intent, routes to the appropriate engine, then synthesizes
    the response as speech.

    For audio input, the client should first call /voice/stt directly,
    then pass the transcript here.

    Ref: orchestra-formation.md §3 Flow E
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    degraded: list[str] = []
    user_id = body.user_id or "anonymous"

    # ── Step 1: Intent Classification (E7) ────────────────────────────────
    intent_data = {"intent": "general", "confidence": 0.0}
    try:
        intent_data = await call_engine(
            "neural_network", "/ai/intent",
            {"message": body.text, "user_id": user_id},
            request_id=request_id,
        )
    except EngineCallError as e:
        logger.warning(f"Intent classification failed: {e}")
        degraded.append("intent_classification")

    # ── Step 2: Route by intent ───────────────────────────────────────────
    intent = (intent_data.get("intent") or "general").lower()
    response_text = ""

    try:
        if intent in ("eligibility", "eligibility_check"):
            # Route to eligibility check
            elig_data = await call_engine(
                "eligibility_rules", "/eligibility/check",
                {"user_id": user_id, "profile": {}},
                request_id=request_id,
            )
            eligible_count = elig_data.get("eligible", 0)
            response_text = (
                f"You are eligible for {eligible_count} schemes. "
                f"Total schemes checked: {elig_data.get('total_schemes_checked', 0)}."
            )

        elif intent in ("scheme_query", "scheme_info", "policy"):
            # Route to RAG pipeline (simplified)
            vector_data = await call_engine(
                "vector_database", "/vectors/search",
                {"query": body.text, "top_k": 3},
                request_id=request_id,
            )
            results = vector_data.get("results", []) if isinstance(vector_data, dict) else []
            passages = [r.get("content", "") for r in results if r.get("content")]

            if passages:
                rag_data = await call_engine(
                    "neural_network", "/ai/rag",
                    {"user_id": user_id, "question": body.text, "context_passages": passages},
                    request_id=request_id,
                    timeout=20.0,
                )
                response_text = rag_data.get("answer", "I could not find relevant information.")
            else:
                chat_data = await call_engine(
                    "neural_network", "/ai/chat",
                    {"user_id": user_id, "message": body.text},
                    request_id=request_id,
                    timeout=20.0,
                )
                response_text = chat_data.get("response", "I could not find relevant information.")

        elif intent == "deadline":
            deadline_data = await call_engine(
                "deadline_monitoring", "/deadlines/check",
                {"user_id": user_id},
                request_id=request_id,
            )
            total = deadline_data.get("total_deadlines", 0)
            critical = deadline_data.get("critical", 0)
            response_text = f"You have {total} upcoming deadlines. {critical} are critical."

        else:
            # Default: conversational chat
            chat_data = await call_engine(
                "neural_network", "/ai/chat",
                {"user_id": user_id, "message": body.text},
                request_id=request_id,
                timeout=20.0,
            )
            response_text = chat_data.get("response", "I'm sorry, I couldn't understand. Please try again.")

    except EngineCallError as e:
        logger.error(f"Voice query routing failed: {e}")
        response_text = "I'm sorry, the service is temporarily unavailable. Please try again."
        degraded.append("intent_routing")

    # ── Step 3: Translate to user language (if needed) ────────────────────
    if body.language != "english" and body.language != "en" and response_text:
        try:
            translate_data = await call_engine(
                "neural_network", "/ai/translate",
                {
                    "text": response_text,
                    "source_lang": "en",
                    "target_lang": body.language,
                },
                request_id=request_id,
            )
            response_text = translate_data.get("translated", response_text)
        except EngineCallError:
            degraded.append("translation")

    # ── Step 4: Text-to-Speech synthesis (E20) ────────────────────────────
    tts_data = {}
    try:
        tts_data = await call_engine(
            "speech_interface", "/speech/tts",
            {"text": response_text, "language": body.language, "user_id": user_id},
            request_id=request_id,
        )
    except EngineCallError as e:
        logger.warning(f"TTS failed: {e}")
        degraded.append("text_to_speech")

    # ── Step 5: Audit ─────────────────────────────────────────────────────
    await audit_log(
        event_type="VOICE_QUERY",
        user_id=user_id,
        payload={
            "query": body.text,
            "language": body.language,
            "intent": intent,
        },
        request_id=request_id,
    )

    return ApiResponse(
        data={
            "query": body.text,
            "response": response_text,
            "intent": intent,
            "language": body.language,
            "audio_session_id": tts_data.get("session_id"),
            "audio_available": tts_data.get("audio_available", False),
            "degraded": degraded if degraded else None,
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSITE ROUTE 6 — Simulation with Explanation (Controller Flow)
# ══════════════════════════════════════════════════════════════════════════════
# Pipeline: Simulate(E17) → optional AI Explanation(E7) → Audit(E3+E13)

@orchestrator_router.post("/simulate", response_model=ApiResponse)
async def orchestrated_simulate(body: SimulateRequest, request: Request, user=Depends(require_auth)):
    """
    What-if simulation with optional AI-generated explanation.
    The simulation is 100% deterministic (E17, inline rules).

    Ref: orchestra-formation.md §3 Flow C
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    degraded: list[str] = []

    # ── Step 1: Run Simulation (E17) ──────────────────────────────────────
    try:
        sim_data = await call_engine(
            "simulation", "/simulate/what-if",
            {
                "user_id": body.user_id,
                "current_profile": body.current_profile,
                "changes": body.changes,
            },
            request_id=request_id,
        )
    except EngineCallError as e:
        raise HTTPException(
            status_code=e.status or 500,
            detail=f"Simulation engine unavailable: {e.detail}",
        )

    # ── Step 2: AI Explanation (E7) — optional ────────────────────────────
    explanation = None
    if body.explain:
        try:
            summary_text = (
                f"Simulation results for user {body.user_id}: "
                f"Changes applied: {body.changes}. "
                f"Before: {sim_data.get('before', {})}. "
                f"After: {sim_data.get('after', {})}. "
                f"Delta: {sim_data.get('delta', {})}."
            )
            summary_data = await call_engine(
                "neural_network", "/ai/summarize",
                {"text": summary_text, "max_length": 300},
                request_id=request_id,
                timeout=15.0,
            )
            explanation = summary_data.get("summary", "")
        except EngineCallError:
            degraded.append("ai_explanation")

    # ── Step 3: Audit ─────────────────────────────────────────────────────
    await audit_log(
        event_type="SIMULATION_RUN",
        user_id=body.user_id,
        payload={"changes": body.changes},
        request_id=request_id,
    )

    return ApiResponse(
        data={
            **sim_data,
            "explanation": explanation,
            "degraded": degraded if degraded else None,
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@orchestrator_router.get("/circuit-breaker/status", tags=["System"])
async def circuit_breaker_status(user=Depends(require_auth)):
    """View circuit breaker states for all engines."""
    return ApiResponse(data=circuit_breaker.get_status())


@orchestrator_router.get("/engines/health", tags=["System"])
async def engines_health_check(user=Depends(require_auth)):
    """
    Probe health of all 21 engines concurrently.
    Returns health status for each engine.
    """
    async def check_one(key: str, url: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{url}/health")
                data = resp.json()
                return {"engine": key, "status": "healthy", "port": url.split(":")[-1], "uptime": data.get("uptime_seconds")}
        except Exception:
            return {"engine": key, "status": "unreachable", "port": url.split(":")[-1]}

    tasks = [check_one(k, v) for k, v in ENGINE_URLS.items() if k != "api_gateway"]
    results = await asyncio.gather(*tasks)

    healthy = sum(1 for r in results if r["status"] == "healthy")
    return ApiResponse(
        data={
            "total": len(results),
            "healthy": healthy,
            "unhealthy": len(results) - healthy,
            "engines": sorted(results, key=lambda r: r["engine"]),
        }
    )
