"""
AIforBharat — API Gateway (Engine 9)
======================================
Single entry point for the entire platform.
Handles: routing, rate limiting, JWT validation, CORS,
circuit breaking, request logging, WebSocket hub.

Port: 8000
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.models import ApiResponse, HealthResponse, ErrorCode, make_error
from shared.database import init_db

from .routes import gateway_router
from .orchestrator import orchestrator_router
from .middleware import RateLimitMiddleware, RequestLoggingMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("api_gateway")

START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown events."""
    logger.info("🚀 API Gateway starting up...")
    await init_db()
    logger.info("✅ Database initialized")
    yield
    logger.info("🛑 API Gateway shutting down...")


app = FastAPI(
    title="AIforBharat API Gateway",
    description="Single entry point for the AIforBharat Personal Civic Operating System. "
                "Routes requests to 21 specialized engines.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware Stack ──────────────────────────────────────────────────────────

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted hosts (local development)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],
)

# Custom rate limiting
app.add_middleware(RateLimitMiddleware)

# Request logging
app.add_middleware(RequestLoggingMiddleware)


# ── Trace ID Middleware ─────────────────────────────────────────────────────
@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    """
    Attach a unique trace ID to every request for end-to-end tracing.
    Uses X-Trace-ID as the universal header name across all engines.
    Also supports legacy X-Request-ID header as fallback input.
    """
    trace_id = (
        request.headers.get("X-Trace-ID")
        or request.headers.get("X-Request-ID")
        or str(uuid.uuid4())
    )
    request.state.request_id = trace_id   # backward compat
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    response.headers["X-Request-ID"] = trace_id  # backward compat
    return response


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health check endpoint."""
    return HealthResponse(
        engine="api_gateway",
        status="healthy",
        version=settings.APP_VERSION,
        uptime_seconds=time.time() - START_TIME,
    )


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", tags=["System"])
async def root():
    """API Gateway root — provides service directory."""
    return ApiResponse(
        message="AIforBharat API Gateway",
        data={
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "engines": 21,
            "docs": "/docs",
            "health": "/health",
            "composite_routes": {
                "query": "POST /api/v1/query — Full RAG pipeline",
                "onboard": "POST /api/v1/onboard — User onboarding pipeline",
                "check_eligibility": "POST /api/v1/check-eligibility — Eligibility + AI explanation",
                "ingest_policy": "POST /api/v1/ingest-policy — Policy ingestion pipeline",
                "voice_query": "POST /api/v1/voice-query — Voice query pipeline",
                "simulate": "POST /api/v1/simulate — What-if simulation + explanation",
            },
            "proxy_routes": {
                "auth": "/api/v1/auth/*",
                "identity": "/api/v1/identity/*",
                "metadata": "/api/v1/metadata/*",
                "eligibility": "/api/v1/eligibility/*",
                "schemes": "/api/v1/schemes/*",
                "simulate_direct": "/api/v1/simulate/*",
                "deadlines": "/api/v1/deadlines/*",
                "ai": "/api/v1/ai/*",
                "dashboard": "/api/v1/dashboard/*",
                "documents": "/api/v1/documents/*",
                "voice": "/api/v1/voice/*",
                "analytics": "/api/v1/analytics/*",
                "trust": "/api/v1/trust/*",
                "profile": "/api/v1/profile/*",
                "policies": "/api/v1/policies/*",
                "raw_data": "/api/v1/raw-data/*",
                "processed_metadata": "/api/v1/processed-metadata/*",
                "vectors": "/api/v1/vectors/*",
                "anomaly": "/api/v1/anomaly/*",
                "chunks": "/api/v1/chunks/*",
                "gov_data": "/api/v1/gov-data/*",
            },
        },
    )


# ── Global Exception Handler ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler returning structured error responses."""
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    logger.error(f"Unhandled exception [trace={trace_id}]: {exc}", exc_info=True)

    # Map known exception types to structured error codes
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        if status_code == 401:
            error = make_error(ErrorCode.AUTH_REQUIRED, str(exc.detail))
        elif status_code == 429:
            error = make_error(ErrorCode.RATE_LIMIT, str(exc.detail))
        elif status_code == 404:
            error = make_error(ErrorCode.NOT_FOUND, str(exc.detail))
        elif status_code == 503:
            error = make_error(ErrorCode.ENGINE_UNAVAILABLE, str(exc.detail))
        elif status_code == 504:
            error = make_error(ErrorCode.ENGINE_TIMEOUT, str(exc.detail))
        else:
            error = make_error(ErrorCode.INTERNAL_ERROR, str(exc.detail))
    else:
        status_code = 500
        error = make_error(
            ErrorCode.INTERNAL_ERROR,
            "Internal server error",
            detail=str(exc) if settings.DEBUG else None,
        )

    return JSONResponse(
        status_code=status_code,
        content=ApiResponse(
            success=False,
            message=error.message,
            errors=[error],
            trace_id=trace_id,
        ).model_dump(mode="json"),
        headers={"X-Trace-ID": trace_id},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPExceptions with structured error format."""
    return await global_exception_handler(request, exc)


# ── Include all route groups ──────────────────────────────────────────────────
app.include_router(orchestrator_router)  # composite routes at /api/v1/*
app.include_router(gateway_router, prefix="/api/v1")  # direct proxy routes


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api-gateway.main:app",
        host="0.0.0.0",
        port=settings.API_GATEWAY_PORT,
        reload=settings.DEBUG,
    )
