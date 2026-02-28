"""
AIforBharat — Login/Register Engine (Engine 1)
================================================
User onboarding gateway: registration, phone OTP auth, JWT sessions.
Local-first: OTP is logged (not sent via SMS), DigiLocker stubbed.

Port: 8001
Endpoints:
  POST /auth/register     — New user registration
  POST /auth/login        — Login with phone + password
  POST /auth/otp/send     — Send OTP (locally logged)
  POST /auth/otp/verify   — Verify OTP
  POST /auth/token/refresh — Refresh JWT
  POST /auth/logout       — Invalidate session
  GET  /auth/me           — Get current user profile
  PUT  /auth/profile      — Update user profile
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import init_db
from shared.models import HealthResponse

from .routes import auth_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("login_register")

START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Login/Register Engine starting...")
    # Import models to ensure tables are created
    from . import models as _  # noqa
    await init_db()
    logger.info("✅ Auth tables initialized")
    yield
    logger.info("🛑 Login/Register Engine shutting down...")


app = FastAPI(
    title="AIforBharat Login/Register Engine",
    description="User onboarding, authentication, OTP, JWT sessions",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        engine="login_register",
        status="healthy",
        version=settings.APP_VERSION,
        uptime_seconds=time.time() - START_TIME,
    )


app.include_router(auth_router, prefix="/auth")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("login-register-engine.main:app", host="0.0.0.0", port=settings.LOGIN_REGISTER_PORT, reload=True)
