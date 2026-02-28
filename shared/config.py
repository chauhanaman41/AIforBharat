"""
AIforBharat — Shared Configuration
===================================
Central configuration for all 21 engines. Local-first development mode.
All engines import from here to ensure consistency.
"""

import os
import secrets
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


# ── Project Paths ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
RAW_STORE_DIR = DATA_DIR / "raw-store"
LOGS_DIR = DATA_DIR / "logs"

# Ensure critical directories exist
for d in [DATA_DIR, CACHE_DIR, RAW_STORE_DIR, LOGS_DIR,
          RAW_STORE_DIR / "hot", RAW_STORE_DIR / "warm", RAW_STORE_DIR / "cold"]:
    d.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """
    Unified settings loaded from environment variables / .env file.
    Local-first: No AWS, no DigiLocker, no external notifications.
    """

    # ── Application ───────────────────────────────────────────────────────
    APP_NAME: str = "AIforBharat"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "local"  # local | staging | production

    # ── Engine Ports (each engine runs on its own port locally) ────────────
    API_GATEWAY_PORT: int = 8000
    LOGIN_REGISTER_PORT: int = 8001
    IDENTITY_ENGINE_PORT: int = 8002
    RAW_DATA_STORE_PORT: int = 8003
    METADATA_ENGINE_PORT: int = 8004
    PROCESSED_METADATA_PORT: int = 8005
    VECTOR_DATABASE_PORT: int = 8006
    NEURAL_NETWORK_PORT: int = 8007
    ANOMALY_DETECTION_PORT: int = 8008
    CHUNKS_ENGINE_PORT: int = 8010
    POLICY_FETCHING_PORT: int = 8011
    JSON_USER_INFO_PORT: int = 8012
    ANALYTICS_WAREHOUSE_PORT: int = 8013
    DASHBOARD_BFF_PORT: int = 8014
    ELIGIBILITY_RULES_PORT: int = 8015
    DEADLINE_MONITORING_PORT: int = 8016
    SIMULATION_ENGINE_PORT: int = 8017
    GOV_DATA_SYNC_PORT: int = 8018
    TRUST_SCORING_PORT: int = 8019
    SPEECH_INTERFACE_PORT: int = 8020
    DOC_UNDERSTANDING_PORT: int = 8021

    # ── Local Data Directory ──────────────────────────────────────────────
    LOCAL_DATA_DIR: str = str(DATA_DIR)

    # ── Database (Local SQLite for MVP, PostgreSQL placeholder) ───────────
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DATA_DIR}/aiforbharat.db"
    SYNC_DATABASE_URL: str = f"sqlite:///{DATA_DIR}/aiforbharat.db"

    # ── Redis (Local fallback to in-memory if Redis unavailable) ──────────
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_REDIS: bool = False  # Set True if Redis is running locally

    # ── NVIDIA AI Stack ───────────────────────────────────────────────────
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_API_KEY: str = "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"
    NVIDIA_API_KEY_2: str = "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"
    NVIDIA_API_KEY_3: str = "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"
    RIVA_API_KEY: str = "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"
    NEMO_API_KEY: str = "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"

    # NIM model identifiers
    NIM_MODEL_70B: str = "meta/llama-3.1-70b-instruct"
    NIM_MODEL_8B: str = "meta/llama-3.1-8b-instruct"
    EMBEDDING_MODEL: str = "nvidia/nv-embedqa-e5-v5"
    RERANK_MODEL: str = "nvidia/rerank-qa-mistral-4b"

    # ── Triton Auth Token (auto-generated) ────────────────────────────────
    TRITON_AUTH_TOKEN: str = Field(default_factory=lambda: secrets.token_hex(32))

    # ── JWT Configuration ─────────────────────────────────────────────────
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_hex(32))
    JWT_ALGORITHM: str = "HS256"  # HS256 for local; RS256 for production
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Encryption ────────────────────────────────────────────────────────
    AES_ENCRYPTION_KEY: str = Field(default_factory=lambda: secrets.token_hex(16))  # 128-bit for AES-256-GCM

    # ── External Data Sources ─────────────────────────────────────────────
    DATA_GOV_API_KEY: str = "579b464db66ec23bdd0000016f17f36372cf48e47f7e5b4ecdb7bb27"
    DATA_GOV_BASE_URL: str = "https://api.data.gov.in/resource"

    # ── Local Data Paths ──────────────────────────────────────────────────
    FINANCE_FILES_DIR: str = r"C:\Users\Amandeep\Downloads\financefiles"
    CENSUS_DATA_PATH: str = r"C:\Users\Amandeep\Downloads\DDW_PCA0000_2011_Indiastatedist.xlsx"
    NFHS5_DATA_PATH: str = r"C:\Users\Amandeep\Downloads\NFHS 5 district wise data\NFHS 5 district wise data\ssrn datasheet.xls"
    POVERTY_DATA_PATH: str = r"C:\Users\Amandeep\Downloads\amandeepsinghchauhan5_17722114987588584.csv"
    SLUM_DATA_PATH: str = r"C:\Users\Amandeep\Downloads\amandeepsinghchauhan5_17722114968323698.csv"
    SDG_DATA_PATH: str = r"C:\Users\Amandeep\Downloads\amandeepsinghchauhan5_17722109276149728.csv"
    TOWN_VILLAGE_DIR_PATH: str = r"C:\Users\Amandeep\Downloads\PC11_TV_DIR.xlsx"
    ASPIRATIONAL_DISTRICTS_PATH: str = r"C:\Users\Amandeep\Downloads\List-of-112-Aspirational-Districts (1).pdf"

    # ── Rate Limiting ─────────────────────────────────────────────────────
    RATE_LIMIT_GLOBAL_RPS: int = 10000
    RATE_LIMIT_PER_USER_RPM: int = 60
    RATE_LIMIT_AI_RPM: int = 20
    RATE_LIMIT_PER_IP_RPM: int = 100

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # ── Crawl Settings ────────────────────────────────────────────────────
    CRAWL_RATE_LIMIT_RPS: float = 2.0  # Requests per second per source
    CRAWL_USER_AGENT: str = "AIforBharat-PolicyBot/1.0 (+https://aifor-bharat.in/bot)"
    CRAWL_RESPECT_ROBOTS_TXT: bool = True

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton settings instance
settings = Settings()


def get_engine_url(port: int) -> str:
    """Get the local URL for an engine by port number."""
    return f"http://localhost:{port}"


# ── Engine URL helpers ────────────────────────────────────────────────────────
ENGINE_URLS = {
    "api_gateway": get_engine_url(settings.API_GATEWAY_PORT),
    "login_register": get_engine_url(settings.LOGIN_REGISTER_PORT),
    "identity": get_engine_url(settings.IDENTITY_ENGINE_PORT),
    "raw_data_store": get_engine_url(settings.RAW_DATA_STORE_PORT),
    "metadata": get_engine_url(settings.METADATA_ENGINE_PORT),
    "processed_metadata": get_engine_url(settings.PROCESSED_METADATA_PORT),
    "vector_database": get_engine_url(settings.VECTOR_DATABASE_PORT),
    "neural_network": get_engine_url(settings.NEURAL_NETWORK_PORT),
    "anomaly_detection": get_engine_url(settings.ANOMALY_DETECTION_PORT),
    "chunks": get_engine_url(settings.CHUNKS_ENGINE_PORT),
    "policy_fetching": get_engine_url(settings.POLICY_FETCHING_PORT),
    "json_user_info": get_engine_url(settings.JSON_USER_INFO_PORT),
    "analytics_warehouse": get_engine_url(settings.ANALYTICS_WAREHOUSE_PORT),
    "dashboard_bff": get_engine_url(settings.DASHBOARD_BFF_PORT),
    "eligibility_rules": get_engine_url(settings.ELIGIBILITY_RULES_PORT),
    "deadline_monitoring": get_engine_url(settings.DEADLINE_MONITORING_PORT),
    "simulation": get_engine_url(settings.SIMULATION_ENGINE_PORT),
    "gov_data_sync": get_engine_url(settings.GOV_DATA_SYNC_PORT),
    "trust_scoring": get_engine_url(settings.TRUST_SCORING_PORT),
    "speech_interface": get_engine_url(settings.SPEECH_INTERFACE_PORT),
    "doc_understanding": get_engine_url(settings.DOC_UNDERSTANDING_PORT),
}
