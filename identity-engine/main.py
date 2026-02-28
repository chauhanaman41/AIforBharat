"""
AIforBharat — Identity Engine (Engine 2)
==========================================
Secure identity vault with AES-256-GCM encrypted PII,
tokenized identities, role management, data export,
and cryptographic deletion (right to forget).

Port: 8002
"""

import logging, time, os, sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.config import settings
from shared.database import init_db
from shared.models import HealthResponse
from .routes import identity_router
from . import models as _  # noqa

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("identity_engine")
START_TIME = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Identity Engine starting...")
    await init_db()
    yield
    logger.info("🛑 Identity Engine shutting down...")

app = FastAPI(title="AIforBharat Identity Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="identity_engine", uptime_seconds=time.time() - START_TIME)

app.include_router(identity_router, prefix="/identity")
