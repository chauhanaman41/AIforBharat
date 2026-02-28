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

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.models import ApiResponse, HealthResponse
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


# ── Request ID Middleware ─────────────────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Attach a unique request ID to every request for tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
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
    """Catch-all exception handler to return consistent error format."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            success=False,
            message="Internal server error",
            errors=[{"detail": str(exc)}],
        ).model_dump(mode="json"),
    )


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
