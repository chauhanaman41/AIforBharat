"""
AIforBharat — Policy Fetching Engine (Engine 11)
==================================================
Data acquisition layer: crawls, caches, and versions government scheme data
from official portals, Gazette of India, budget documents, and data.gov.in.
Implements change detection, diff storage, and source health monitoring.
All data cached locally first (Local-First constraint).

Port: 8011
"""

import logging, time, os, sys, json, hashlib, asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Float, Boolean, Integer, Text, DateTime, JSON, select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.utils import generate_id, sha256_hash
from shared.cache import LocalCache, file_exists_locally

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("policy_fetching_engine")
START_TIME = time.time()

POLICY_STORE_DIR = Path(settings.LOCAL_DATA_DIR) / "policies"
POLICY_STORE_DIR.mkdir(parents=True, exist_ok=True)
policy_cache = LocalCache(namespace="policies", ttl=3600)


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class FetchedDocument(Base):
    __tablename__ = "fetched_documents"
    id = Column(String, primary_key=True, default=generate_id)
    source_id = Column(String, index=True, nullable=False)
    source_url = Column(Text, nullable=False)
    document_type = Column(String)             # gazette, notification, circular, budget, scheme
    format = Column(String, default="html")    # pdf, html, json, xml
    title = Column(String)
    ministry = Column(String)
    notification_number = Column(String)
    publication_date = Column(String)
    effective_date = Column(String)
    states_affected = Column(Text)             # JSON array
    policy_id = Column(String, index=True)
    content_hash = Column(String)
    content_size_bytes = Column(Integer, default=0)
    local_storage_path = Column(Text)
    raw_content = Column(Text)
    extracted_text = Column(Text)
    version = Column(Integer, default=1)
    previous_version_hash = Column(String)
    change_type = Column(String)               # new, amendment, correction, repeal
    change_summary = Column(String)
    processing_status = Column(String, default="fetched")  # fetched, parsed, sent_to_chunks, error
    fetch_timestamp = Column(DateTime, default=datetime.utcnow)
    next_crawl_at = Column(DateTime)


class SourceConfig(Base):
    __tablename__ = "source_configs"
    id = Column(String, primary_key=True, default=generate_id)
    source_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    url = Column(Text, nullable=False)
    source_type = Column(String, default="api")     # api, scraper, rss
    schedule_cron = Column(String, default="0 */6 * * *")
    api_key_env = Column(String)
    rate_limit_per_sec = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    last_crawled_at = Column(DateTime)
    last_status = Column(String, default="pending")  # success, failed, partial
    total_crawls = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Built-in Source Definitions ───────────────────────────────────────────────

DEFAULT_SOURCES = [
    {
        "source_id": "data_gov_in",
        "name": "data.gov.in",
        "url": "https://api.data.gov.in/resource/",
        "source_type": "api",
        "schedule_cron": "0 */6 * * *",
        "api_key_env": "DATA_GOV_API_KEY",
        "rate_limit_per_sec": 5.0,
    },
    {
        "source_id": "gazette_india",
        "name": "Gazette of India",
        "url": "https://egazette.gov.in/",
        "source_type": "scraper",
        "schedule_cron": "*/30 * * * *",
        "rate_limit_per_sec": 1.0,
    },
    {
        "source_id": "pmkisan_portal",
        "name": "PM-KISAN Portal",
        "url": "https://pmkisan.gov.in/",
        "source_type": "scraper",
        "schedule_cron": "0 0 * * *",
        "rate_limit_per_sec": 1.0,
    },
    {
        "source_id": "myscheme_gov",
        "name": "MyScheme Portal",
        "url": "https://www.myscheme.gov.in/",
        "source_type": "scraper",
        "schedule_cron": "0 */12 * * *",
        "rate_limit_per_sec": 1.0,
    },
    {
        "source_id": "rbi_notifications",
        "name": "RBI Notifications",
        "url": "https://www.rbi.org.in/scripts/BS_CircularIndexDisplay.aspx",
        "source_type": "scraper",
        "schedule_cron": "0 */4 * * *",
        "rate_limit_per_sec": 1.0,
    },
]

# ── Pre-loaded scheme data for local-first ────────────────────────────────────

SEED_SCHEMES = [
    {
        "policy_id": "PM-KISAN-2024",
        "title": "Pradhan Mantri Kisan Samman Nidhi",
        "ministry": "Agriculture and Farmers Welfare",
        "document_type": "scheme",
        "content": """PM-KISAN provides income support of Rs 6000 per year to all landholding farmer families.
Eligibility: All landholding farmer families with cultivable land.
Income Limit: Family income below Rs 2,00,000 per annum (excluding institutional landholders).
Benefits: Rs 2000 every 4 months directly to bank account.
Documents: Aadhaar, Land records, Bank account.
States: All India.
Category: Agriculture, Direct Benefit Transfer.""",
    },
    {
        "policy_id": "PM-AWAS-YOJANA-2024",
        "title": "Pradhan Mantri Awas Yojana (Urban & Gramin)",
        "ministry": "Housing and Urban Affairs",
        "document_type": "scheme",
        "content": """Housing for All scheme providing assistance for construction/purchase of houses.
Urban: Credit-linked subsidy (CLSS) for EWS/LIG/MIG categories. Subsidy up to Rs 2.67 lakh.
Gramin: Financial assistance of Rs 1.20 lakh (plain) and Rs 1.30 lakh (hilly/difficult areas).
Eligibility: No pucca house in family name, EWS/LIG/MIG income criteria.
Category: Housing, EWS, LIG, BPL.""",
    },
    {
        "policy_id": "AYUSHMAN-BHARAT-2024",
        "title": "Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (AB-PMJAY)",
        "ministry": "Health and Family Welfare",
        "document_type": "scheme",
        "content": """Health insurance of Rs 5 lakh per family per year for secondary and tertiary hospitalization.
Eligibility: Based on deprivation and occupational criteria from SECC data.
Covers: 1,929+ treatment packages including surgeries, day care, ICU.
Pre-existing conditions covered from day one.
Cashless and paperless at empanelled hospitals.
Category: Healthcare, BPL, Insurance.""",
    },
    {
        "policy_id": "PM-UJJWALA-2024",
        "title": "Pradhan Mantri Ujjwala Yojana",
        "ministry": "Petroleum and Natural Gas",
        "document_type": "scheme",
        "content": """Free LPG connections for women from BPL households.
Eligibility: Women from BPL families, SC/ST, PMAY beneficiaries, Antyodaya Anna Yojana.
Benefit: Free LPG connection (Rs 1600 subsidy), first refill free.
Category: Energy, Women, BPL.""",
    },
    {
        "policy_id": "MUDRA-YOJANA-2024",
        "title": "Pradhan Mantri MUDRA Yojana",
        "ministry": "Finance",
        "document_type": "scheme",
        "content": """Loans up to Rs 10 lakh to non-corporate, non-farm small/micro enterprises.
Shishu: Loan up to Rs 50,000 | Kishore: Rs 50,001 to Rs 5,00,000 | Tarun: Rs 5,00,001 to Rs 10,00,000.
No collateral required. Available through all banks and MFIs.
Eligibility: Any Indian citizen with a business plan for non-farm income-generating activity.
Category: Enterprise, Self-employment, MSME.""",
    },
    {
        "policy_id": "PMSBY-2024",
        "title": "Pradhan Mantri Suraksha Bima Yojana",
        "ministry": "Finance",
        "document_type": "scheme",
        "content": """Accident insurance cover of Rs 2 lakh at Rs 20 per annum.
Eligibility: Age 18-70, savings bank account, Aadhaar linked.
Covers: Accidental death (Rs 2 lakh), total permanent disability (Rs 2 lakh), partial disability (Rs 1 lakh).
Category: Insurance, Accident, Low-premium.""",
    },
    {
        "policy_id": "PMJJBY-2024",
        "title": "Pradhan Mantri Jeevan Jyoti Bima Yojana",
        "ministry": "Finance",
        "document_type": "scheme",
        "content": """Life insurance cover of Rs 2 lakh at Rs 436 per annum.
Eligibility: Age 18-50, savings bank account.
Coverage: Death due to any reason. Renewable annually.
Category: Insurance, Life, Low-premium.""",
    },
    {
        "policy_id": "SUKANYA-SAMRIDDHI-2024",
        "title": "Sukanya Samriddhi Yojana",
        "ministry": "Finance",
        "document_type": "scheme",
        "content": """Savings scheme for girl child. Current interest rate ~8%.
Eligibility: Girl child below 10 years. Max 2 accounts per family.
Min deposit: Rs 250/year. Max: Rs 1,50,000/year. Tax benefit under 80C.
Maturity: 21 years from account opening.
Category: Girl Child, Savings, Tax-benefit.""",
    },
    {
        "policy_id": "NATIONAL-PENSION-2024",
        "title": "National Pension System (NPS)",
        "ministry": "Finance",
        "document_type": "scheme",
        "content": """Voluntary pension scheme for systematic savings during working life.
Eligibility: Indian citizens aged 18-70. Additional tax benefit of Rs 50,000 under 80CCD(1B).
Employer contribution exempt up to 14% (govt) / 10% (private) of salary.
Min contribution: Rs 1,000/year. Partial withdrawal allowed after 3 years.
Category: Pension, Retirement, Tax-benefit.""",
    },
    {
        "policy_id": "SCHOLARSHIP-SC-ST-2024",
        "title": "Post-Matric Scholarship for SC/ST Students",
        "ministry": "Social Justice and Empowerment",
        "document_type": "scheme",
        "content": """Scholarships for SC/ST students studying post-matriculation courses.
Eligibility: SC/ST category, family income below Rs 2.5 lakh/year.
Covers: Fees, maintenance allowance, book grant.
Category: Education, SC/ST, Scholarship.""",
    },
]


# ── Schemas ───────────────────────────────────────────────────────────────────

class FetchRequest(BaseModel):
    source_id: str
    url: Optional[str] = None
    document_type: str = "scheme"
    content: Optional[str] = None
    metadata: dict = {}


class AddSourceRequest(BaseModel):
    source_id: str
    name: str
    url: str
    source_type: str = "api"
    schedule_cron: str = "0 */6 * * *"
    rate_limit_per_sec: float = 1.0


class SchemeFetchRequest(BaseModel):
    """Schema used by the Orchestrator's ingest-policy composite route."""
    source_url: str
    source_type: str = "web"
    tags: Optional[List[str]] = None


class PolicySearchRequest(BaseModel):
    query: str
    ministry: Optional[str] = None
    document_type: Optional[str] = None
    limit: int = 10


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Policy Fetching Engine starting...")
    await init_db()
    # Seed default sources and policies
    await _seed_sources()
    await _seed_policies()
    yield

app = FastAPI(title="AIforBharat Policy Fetching Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


async def _seed_sources():
    """Seed default crawl sources into DB."""
    async with AsyncSessionLocal() as session:
        for src in DEFAULT_SOURCES:
            exists = (await session.execute(
                select(SourceConfig).where(SourceConfig.source_id == src["source_id"])
            )).scalar_one_or_none()
            if not exists:
                session.add(SourceConfig(**src, id=generate_id()))
        await session.commit()
    logger.info(f"Seeded {len(DEFAULT_SOURCES)} default sources")


async def _seed_policies():
    """Seed pre-loaded scheme data so the system works offline (Local-First)."""
    async with AsyncSessionLocal() as session:
        for scheme in SEED_SCHEMES:
            exists = (await session.execute(
                select(FetchedDocument).where(FetchedDocument.policy_id == scheme["policy_id"])
            )).scalar_one_or_none()
            if not exists:
                content = scheme["content"]
                content_hash = sha256_hash(content)

                # Store to local filesystem
                safe_name = scheme["policy_id"].replace(" ", "_")
                local_path = POLICY_STORE_DIR / f"{safe_name}.txt"
                local_path.write_text(content, encoding="utf-8")

                doc = FetchedDocument(
                    id=generate_id(),
                    source_id="seed_data",
                    source_url="local://seed",
                    document_type=scheme["document_type"],
                    format="text",
                    title=scheme["title"],
                    ministry=scheme.get("ministry"),
                    policy_id=scheme["policy_id"],
                    content_hash=content_hash,
                    content_size_bytes=len(content.encode()),
                    local_storage_path=str(local_path),
                    raw_content=content,
                    extracted_text=content,
                    change_type="new",
                    processing_status="parsed",
                )
                session.add(doc)

                # Cache it
                policy_cache.set(f"policy:{scheme['policy_id']}", {
                    "policy_id": scheme["policy_id"],
                    "title": scheme["title"],
                    "ministry": scheme.get("ministry"),
                    "content": content,
                })

        await session.commit()
    logger.info(f"Seeded {len(SEED_SCHEMES)} pre-loaded schemes")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="policy_fetching_engine", uptime_seconds=time.time() - START_TIME)


@app.post("/policies/fetch", response_model=ApiResponse, tags=["Fetch"])
async def fetch_document(data: FetchRequest, bg: BackgroundTasks):
    """
    Fetch and store a policy document.
    Implements change detection via content hash comparison.
    Stores content locally first (Local-First).
    """
    content = data.content or ""
    content_hash = sha256_hash(content) if content else ""

    # Change detection
    async with AsyncSessionLocal() as session:
        existing = None
        if data.metadata.get("policy_id"):
            existing = (await session.execute(
                select(FetchedDocument).where(
                    FetchedDocument.policy_id == data.metadata.get("policy_id")
                ).order_by(FetchedDocument.version.desc())
            )).scalars().first()

        is_new = existing is None
        is_changed = existing and existing.content_hash != content_hash
        version = (existing.version + 1) if existing else 1
        change_type = "new" if is_new else ("amendment" if is_changed else "unchanged")

        if not is_new and not is_changed:
            return ApiResponse(message="Document unchanged, skipping", data={"change_type": "unchanged"})

        # Store locally
        safe_name = f"{data.source_id}_{generate_id()[:8]}.txt"
        local_path = POLICY_STORE_DIR / safe_name
        local_path.write_text(content, encoding="utf-8")

        doc = FetchedDocument(
            id=generate_id(),
            source_id=data.source_id,
            source_url=data.url or "",
            document_type=data.document_type,
            title=data.metadata.get("title", ""),
            ministry=data.metadata.get("ministry", ""),
            policy_id=data.metadata.get("policy_id"),
            content_hash=content_hash,
            content_size_bytes=len(content.encode()),
            local_storage_path=str(local_path),
            raw_content=content,
            extracted_text=content,
            version=version,
            previous_version_hash=existing.content_hash if existing else None,
            change_type=change_type,
            change_summary=data.metadata.get("change_summary", ""),
            processing_status="parsed",
        )
        session.add(doc)

        # Update source health
        src = (await session.execute(
            select(SourceConfig).where(SourceConfig.source_id == data.source_id)
        )).scalar_one_or_none()
        if src:
            src.last_crawled_at = datetime.utcnow()
            src.last_status = "success"
            src.total_crawls = (src.total_crawls or 0) + 1
            src.success_count = (src.success_count or 0) + 1

        await session.commit()

    # Publish events
    event_type = EventType.DOCUMENT_FETCHED if is_new else EventType.DOCUMENT_UPDATED
    await event_bus.publish(EventMessage(
        event_type=event_type,
        source_engine="policy_fetching_engine",
        payload={
            "policy_id": data.metadata.get("policy_id"),
            "title": data.metadata.get("title"),
            "change_type": change_type,
            "version": version,
        },
    ))

    # Cache
    if data.metadata.get("policy_id"):
        policy_cache.set(f"policy:{data.metadata['policy_id']}", {
            "policy_id": data.metadata["policy_id"],
            "title": data.metadata.get("title"),
            "content": content,
            "version": version,
        })

    return ApiResponse(message=f"Document {change_type}", data={
        "change_type": change_type, "version": version,
        "content_hash": content_hash,
    })


@app.get("/policies/list", response_model=ApiResponse, tags=["Query"])
async def list_policies(
    source_id: Optional[str] = None,
    document_type: Optional[str] = None,
    ministry: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    """List fetched policy documents with filtering."""
    async with AsyncSessionLocal() as session:
        query = select(FetchedDocument).order_by(FetchedDocument.fetch_timestamp.desc())
        if source_id:
            query = query.where(FetchedDocument.source_id == source_id)
        if document_type:
            query = query.where(FetchedDocument.document_type == document_type)
        if ministry:
            query = query.where(FetchedDocument.ministry.ilike(f"%{ministry}%"))
        query = query.offset(offset).limit(limit)

        results = (await session.execute(query)).scalars().all()
        return ApiResponse(data=[{
            "id": r.id, "policy_id": r.policy_id, "title": r.title,
            "ministry": r.ministry, "document_type": r.document_type,
            "source_id": r.source_id, "version": r.version,
            "change_type": r.change_type, "content_hash": r.content_hash,
            "processing_status": r.processing_status,
            "fetched_at": r.fetch_timestamp.isoformat() if r.fetch_timestamp else None,
        } for r in results], metadata={"count": len(results), "offset": offset})


@app.get("/policies/{policy_id}", response_model=ApiResponse, tags=["Query"])
async def get_policy(policy_id: str):
    """Get a specific policy with full content."""
    cached = policy_cache.get(f"policy:{policy_id}")
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(FetchedDocument)
            .where(FetchedDocument.policy_id == policy_id)
            .order_by(FetchedDocument.version.desc())
        )).scalars().first()
        if not row:
            raise HTTPException(status_code=404, detail="Policy not found")

        data = {
            "policy_id": row.policy_id, "title": row.title,
            "ministry": row.ministry, "content": row.extracted_text or row.raw_content,
            "version": row.version, "document_type": row.document_type,
            "change_type": row.change_type, "content_hash": row.content_hash,
        }
        policy_cache.set(f"policy:{policy_id}", data)
        return ApiResponse(data=data)


@app.get("/policies/{policy_id}/versions", response_model=ApiResponse, tags=["Query"])
async def get_policy_versions(policy_id: str):
    """Get version history for a policy."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(FetchedDocument)
            .where(FetchedDocument.policy_id == policy_id)
            .order_by(FetchedDocument.version.desc())
        )).scalars().all()
        return ApiResponse(data=[{
            "version": r.version, "change_type": r.change_type,
            "change_summary": r.change_summary, "content_hash": r.content_hash,
            "fetched_at": r.fetch_timestamp.isoformat() if r.fetch_timestamp else None,
        } for r in rows])


@app.post("/policies/search", response_model=ApiResponse, tags=["Query"])
async def search_policies(data: PolicySearchRequest):
    """Search policies by keyword, ministry, or document type."""
    async with AsyncSessionLocal() as session:
        query = select(FetchedDocument)
        if data.query:
            query = query.where(
                (FetchedDocument.title.ilike(f"%{data.query}%")) |
                (FetchedDocument.extracted_text.ilike(f"%{data.query}%"))
            )
        if data.ministry:
            query = query.where(FetchedDocument.ministry.ilike(f"%{data.ministry}%"))
        if data.document_type:
            query = query.where(FetchedDocument.document_type == data.document_type)
        query = query.order_by(FetchedDocument.fetch_timestamp.desc()).limit(data.limit)

        results = (await session.execute(query)).scalars().all()
        return ApiResponse(data=[{
            "policy_id": r.policy_id, "title": r.title,
            "ministry": r.ministry, "snippet": (r.extracted_text or "")[:300],
            "document_type": r.document_type, "version": r.version,
        } for r in results])


# ── Source Management ─────────────────────────────────────────────────────────

@app.get("/policies/sources/list", response_model=ApiResponse, tags=["Sources"])
async def list_sources():
    """List all configured data sources with health metrics."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(SourceConfig))).scalars().all()
        return ApiResponse(data=[{
            "source_id": r.source_id, "name": r.name, "url": r.url,
            "type": r.source_type, "schedule": r.schedule_cron,
            "is_active": r.is_active, "total_crawls": r.total_crawls,
            "success_rate": round(r.success_count / max(r.total_crawls, 1) * 100, 1),
            "last_crawled": r.last_crawled_at.isoformat() if r.last_crawled_at else None,
            "last_status": r.last_status,
        } for r in rows])


@app.post("/policies/sources/add", response_model=ApiResponse, tags=["Sources"])
async def add_source(data: AddSourceRequest):
    """Add a new data source for crawling."""
    async with AsyncSessionLocal() as session:
        existing = (await session.execute(
            select(SourceConfig).where(SourceConfig.source_id == data.source_id)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Source already exists")

        session.add(SourceConfig(
            id=generate_id(), source_id=data.source_id,
            name=data.name, url=data.url, source_type=data.source_type,
            schedule_cron=data.schedule_cron, rate_limit_per_sec=data.rate_limit_per_sec,
        ))
        await session.commit()
    return ApiResponse(message="Source added")


# ── Orchestrator-compatible fetch endpoint ────────────────────────────────────

@app.post("/schemes/fetch", response_model=ApiResponse, tags=["Fetch"])
async def fetch_scheme_by_url(data: SchemeFetchRequest):
    """
    Fetch a policy/scheme by URL.  Used by the API-Gateway orchestrator's
    ingest-policy composite route.

    Local-first behaviour:
      1. Search seeded policies whose source_url or title partially matches.
      2. If found, return the cached content immediately.
      3. If not found, return a synthetic stub so the pipeline can proceed.
    """
    # Try to match against already-seeded / fetched documents
    async with AsyncSessionLocal() as session:
        # Exact source_url match first
        row = (await session.execute(
            select(FetchedDocument)
            .where(FetchedDocument.source_url.ilike(f"%{data.source_url}%"))
            .order_by(FetchedDocument.version.desc())
        )).scalars().first()

        # Fallback: try keyword match from URL components
        if not row:
            raw_keywords = [
                kw for kw in data.source_url
                .replace("https://", "").replace("http://", "")
                .replace("/", " ").replace(".", " ")
                .split()
                if len(kw) > 3
            ]
            # Generate keyword variants to handle schemes like pmkisan <-> PM-KISAN
            keywords: list[str] = []
            for kw in raw_keywords:
                keywords.append(kw)                          # pmkisan
                if "-" in kw:
                    keywords.append(kw.replace("-", ""))      # pm-kisan → pmkisan
                    keywords.append(kw.replace("-", "%"))     # pm-kisan → pm%kisan
                # For compound words (e.g. pmkisan), insert wildcard after
                # common 2-char Indian-scheme prefixes like pm, ab
                if len(kw) >= 5 and kw[:2].lower() in ("pm", "ab"):
                    keywords.append(f"{kw[:2]}%{kw[2:]}")    # pmkisan → pm%kisan
                    keywords.append(kw[2:])                   # pmkisan → kisan

            for kw in keywords:
                row = (await session.execute(
                    select(FetchedDocument)
                    .where(
                        (FetchedDocument.title.ilike(f"%{kw}%")) |
                        (FetchedDocument.extracted_text.ilike(f"%{kw}%")) |
                        (FetchedDocument.policy_id.ilike(f"%{kw}%"))
                    )
                    .order_by(FetchedDocument.version.desc())
                )).scalars().first()
                if row:
                    break

    if row:
        return ApiResponse(
            message="Policy fetched from local store",
            data={
                "document_id": row.id,
                "policy_id": row.policy_id,
                "scheme_id": row.policy_id,
                "title": row.title,
                "text": row.extracted_text or row.raw_content or "",
                "content": row.extracted_text or row.raw_content or "",
                "source_url": data.source_url,
                "version": row.version,
                "change_type": "existing",
            },
        )

    # No match — return a synthetic stub so downstream steps can still run
    stub_id = generate_id()
    stub_text = (
        f"Stub policy document fetched from {data.source_url}. "
        "This is a locally generated placeholder. In production the content "
        "would be crawled from the source portal."
    )
    return ApiResponse(
        message="Policy stub generated (source not yet crawled)",
        data={
            "document_id": stub_id,
            "policy_id": f"stub_{stub_id[:8]}",
            "scheme_id": f"stub_{stub_id[:8]}",
            "title": f"Policy from {data.source_url}",
            "text": stub_text,
            "content": stub_text,
            "source_url": data.source_url,
            "version": 1,
            "change_type": "new",
        },
    )
