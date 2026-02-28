"""
AIforBharat — Shared Database Setup
=====================================
Local SQLite database with async support via aiosqlite.
Each engine can create its own tables using the shared Base.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from shared.config import settings, DATA_DIR


# ── SQLAlchemy Base ───────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Declarative base for all ORM models across engines."""
    pass


# ── Async Engine (for FastAPI async endpoints) ────────────────────────────────
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Sync Engine (for migrations, scripts, seed data) ─────────────────────────
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
)


# Enable WAL mode for SQLite (better concurrent read/write performance)
@event.listens_for(sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def get_async_session() -> AsyncSession:
    """Dependency for FastAPI endpoints to get an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_session() -> Session:
    """Get a synchronous database session."""
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


async def init_db():
    """Create all tables in the database. Called at application startup."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Dispose of all database connections. Called at application shutdown."""
    await async_engine.dispose()
