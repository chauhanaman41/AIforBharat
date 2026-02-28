"""
AIforBharat — Document Understanding Engine (Engine 21)
========================================================
Processes government policy documents (PDF, HTML, text) into structured
fields: eligibility criteria, benefits, deadlines, required documents.
Uses NVIDIA NIM for NLP extraction when available, falls back to
rule-based parsing.

Port: 8021
"""

import logging, time, os, sys, json, re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, JSON, select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.nvidia_client import nvidia_client
from shared.utils import generate_id, sha256_hash
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("document_understanding_engine")
START_TIME = time.time()
doc_cache = LocalCache(namespace="doc_understanding", ttl=3600)


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class ParsedDocument(Base):
    __tablename__ = "parsed_documents"
    id = Column(String, primary_key=True, default=generate_id)
    source_document_id = Column(String, index=True)
    policy_id = Column(String, index=True)
    title = Column(String)
    raw_text = Column(Text)
    structured_data = Column(Text)    # Full JSON of extracted structure
    eligibility_criteria = Column(Text)  # JSON array
    benefits = Column(Text)              # JSON array
    required_documents = Column(Text)    # JSON array
    deadlines = Column(Text)            # JSON array
    income_limits = Column(Text)        # JSON
    age_limits = Column(Text)           # JSON
    target_categories = Column(Text)    # JSON array (SC, ST, OBC, EWS, BPL, etc.)
    target_states = Column(Text)        # JSON array
    ministry = Column(String)
    scheme_type = Column(String)        # cash_transfer, subsidy, insurance, loan, pension, scholarship
    application_url = Column(String)
    confidence_score = Column(Float, default=0.0)
    extraction_method = Column(String, default="rule_based")  # rule_based, nim_llm, hybrid
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Rule-Based Extraction ─────────────────────────────────────────────────────

ELIGIBILITY_KEYWORDS = [
    "eligib", "who can apply", "qualifying", "criteria", "conditions",
    "requirement", "must be", "should be", "age between", "income below",
    "income limit", "bpl", "belong to", "category", "applicable to",
]

BENEFIT_KEYWORDS = [
    "benefit", "amount", "subsidy", "grant", "loan", "insurance",
    "cover", "paid", "disburse", "transfer", "receive", "entitle",
    "rs ", "rs.", "₹", "lakh", "crore", "per month", "per year",
]

DOCUMENT_KEYWORDS = [
    "document", "aadhaar", "aadhar", "pan card", "ration card",
    "bank account", "certificate", "proof", "income certificate",
    "caste certificate", "domicile", "passport", "voter id",
]

DEADLINE_KEYWORDS = [
    "deadline", "last date", "apply before", "valid till", "expiry",
    "effective from", "effective date", "last day", "closing date",
]


def _extract_section(text: str, keywords: list, window: int = 500) -> List[str]:
    """Extract text sections around keyword matches."""
    text_lower = text.lower()
    sections = []
    for kw in keywords:
        idx = text_lower.find(kw)
        while idx != -1:
            start = max(0, idx - 50)
            end = min(len(text), idx + window)
            snippet = text[start:end].strip()
            if snippet and snippet not in sections:
                sections.append(snippet)
            idx = text_lower.find(kw, idx + len(kw))
    return sections[:10]  # Cap at 10 sections


def _extract_amounts(text: str) -> List[dict]:
    """Extract monetary amounts from text."""
    amounts = []
    # Match patterns like Rs 6000, Rs. 2,00,000, ₹5 lakh, Rs 2.67 lakh
    patterns = [
        r'(?:Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:lakh|lac|crore)?',
        r'(?:Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:per\s+(?:month|year|annum))',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            amount_str = match.group(1).replace(',', '')
            try:
                val = float(amount_str)
                context = text[max(0, match.start()-30):match.end()+50]
                if 'lakh' in context.lower():
                    val *= 100000
                elif 'crore' in context.lower():
                    val *= 10000000
                amounts.append({"amount": val, "context": context.strip()})
            except ValueError:
                pass
    return amounts


def _extract_age_limits(text: str) -> dict:
    """Extract age-related limits."""
    result = {}
    patterns = [
        (r'age\s*(?:between|from)?\s*(\d+)\s*(?:to|-)\s*(\d+)', 'range'),
        (r'(?:above|over|minimum age)\s*(\d+)\s*(?:years?)?', 'min'),
        (r'(?:below|under|maximum age|up to)\s*(\d+)\s*(?:years?)?', 'max'),
    ]
    for pattern, ptype in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if ptype == 'range':
                result["min_age"] = int(match.group(1))
                result["max_age"] = int(match.group(2))
            elif ptype == 'min':
                result["min_age"] = int(match.group(1))
            elif ptype == 'max':
                result["max_age"] = int(match.group(1))
    return result


def _extract_income_limits(text: str) -> dict:
    """Extract income-related limits."""
    result = {}
    patterns = [
        r'(?:income|earning).*?(?:below|under|less than|up to|not exceeding).*?(?:Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore)?',
        r'(?:Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore)?.*?(?:income|earning)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = float(match.group(1).replace(',', ''))
            unit = match.group(2)
            if unit and unit.lower() in ('lakh', 'lac'):
                val *= 100000
            elif unit and unit.lower() == 'crore':
                val *= 10000000
            result["max_annual_income"] = val
            break
    return result


def _extract_categories(text: str) -> List[str]:
    """Extract target demographic categories."""
    categories = []
    category_map = {
        "SC": [r'\bsc\b', r'scheduled\s+caste'],
        "ST": [r'\bst\b', r'scheduled\s+tribe'],
        "OBC": [r'\bobc\b', r'other\s+backward'],
        "EWS": [r'\bews\b', r'economically\s+weaker'],
        "BPL": [r'\bbpl\b', r'below\s+poverty'],
        "Women": [r'\bwomen\b', r'\bfemale\b', r'\bmahila\b'],
        "Senior Citizen": [r'senior\s+citizen', r'elderly', r'age.*?60'],
        "Farmer": [r'\bfarmer\b', r'\bkisan\b', r'agricultur'],
        "Student": [r'\bstudent\b', r'scholarship'],
        "Disabled": [r'disab', r'divyang', r'handicap', r'pwbd'],
        "Minority": [r'minority', r'minorities'],
    }
    text_lower = text.lower()
    for cat, patterns in category_map.items():
        for p in patterns:
            if re.search(p, text_lower):
                categories.append(cat)
                break
    return categories


def rule_based_extract(text: str) -> dict:
    """Full rule-based extraction pipeline."""
    return {
        "eligibility_criteria": _extract_section(text, ELIGIBILITY_KEYWORDS),
        "benefits": _extract_section(text, BENEFIT_KEYWORDS),
        "required_documents": _extract_section(text, DOCUMENT_KEYWORDS),
        "deadlines": _extract_section(text, DEADLINE_KEYWORDS),
        "amounts": _extract_amounts(text),
        "age_limits": _extract_age_limits(text),
        "income_limits": _extract_income_limits(text),
        "target_categories": _extract_categories(text),
    }


# ── NIM-Based Extraction ─────────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are a government policy document analyst. Extract structured information from the following Indian government scheme/policy document.

Return a JSON object with EXACTLY these keys:
- eligibility_criteria: array of strings describing who is eligible
- benefits: array of strings describing what benefits are provided
- required_documents: array of strings listing required documents
- deadlines: array of strings with any deadlines or dates mentioned
- income_limits: object with max_annual_income (number) if mentioned
- age_limits: object with min_age/max_age (numbers) if mentioned
- target_categories: array of applicable categories from [SC, ST, OBC, EWS, BPL, Women, Senior Citizen, Farmer, Student, Disabled, Minority, General]
- scheme_type: one of [cash_transfer, subsidy, insurance, loan, pension, scholarship, housing, healthcare, employment, other]
- key_amounts: array of {amount: number, description: string}

Document text:
{text}

Important: Return ONLY valid JSON, no markdown formatting."""


async def nim_extract(text: str) -> Optional[dict]:
    """Use NVIDIA NIM LLM to extract structured data from policy text."""
    try:
        truncated = text[:4000]  # NIM context limit
        response = await nvidia_client.generate_text(
            EXTRACTION_PROMPT.format(text=truncated),
            max_tokens=2000,
            temperature=0.1,
        )
        # Parse JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        logger.warning(f"NIM extraction failed: {e}")
    return None


# ── Schemas ───────────────────────────────────────────────────────────────────

class ParseDocumentRequest(BaseModel):
    document_id: Optional[str] = None
    policy_id: Optional[str] = None
    title: str = ""
    text: str
    ministry: Optional[str] = None
    use_nim: bool = True


class BatchParseRequest(BaseModel):
    documents: List[ParseDocumentRequest]


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Document Understanding Engine starting...")
    await init_db()
    yield

app = FastAPI(title="AIforBharat Document Understanding Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="document_understanding_engine", uptime_seconds=time.time() - START_TIME)


@app.post("/documents/parse", response_model=ApiResponse, tags=["Parse"])
async def parse_document(data: ParseDocumentRequest):
    """
    Parse a policy document text into structured fields.
    Uses hybrid approach: rule-based first, then NIM LLM for enrichment.
    
    Input: Raw document text
    Output: Structured eligibility criteria, benefits, documents, deadlines, amounts
    """
    cache_key = f"parsed:{sha256_hash(data.text[:500])}"
    cached = doc_cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    # Rule-based extraction (always runs)
    rule_result = rule_based_extract(data.text)
    extraction_method = "rule_based"
    confidence = 0.6

    # NIM enrichment (optional)
    nim_result = None
    if data.use_nim:
        nim_result = await nim_extract(data.text)
        if nim_result:
            extraction_method = "hybrid"
            confidence = 0.85
            # Merge: NIM takes priority, rule-based fills gaps
            for key in ["eligibility_criteria", "benefits", "required_documents", "deadlines", "target_categories"]:
                nim_val = nim_result.get(key, [])
                rule_val = rule_result.get(key, [])
                if nim_val:
                    rule_result[key] = nim_val
                elif rule_val:
                    rule_result[key] = rule_val

            for key in ["age_limits", "income_limits"]:
                nim_val = nim_result.get(key, {})
                if nim_val:
                    rule_result[key] = nim_val

            if nim_result.get("scheme_type"):
                rule_result["scheme_type"] = nim_result["scheme_type"]
            if nim_result.get("key_amounts"):
                rule_result["amounts"] = nim_result["key_amounts"]

    # Store to DB
    async with AsyncSessionLocal() as session:
        doc = ParsedDocument(
            id=generate_id(),
            source_document_id=data.document_id,
            policy_id=data.policy_id,
            title=data.title,
            raw_text=data.text[:10000],
            structured_data=json.dumps(rule_result),
            eligibility_criteria=json.dumps(rule_result.get("eligibility_criteria", [])),
            benefits=json.dumps(rule_result.get("benefits", [])),
            required_documents=json.dumps(rule_result.get("required_documents", [])),
            deadlines=json.dumps(rule_result.get("deadlines", [])),
            income_limits=json.dumps(rule_result.get("income_limits", {})),
            age_limits=json.dumps(rule_result.get("age_limits", {})),
            target_categories=json.dumps(rule_result.get("target_categories", [])),
            ministry=data.ministry,
            scheme_type=rule_result.get("scheme_type"),
            confidence_score=confidence,
            extraction_method=extraction_method,
        )
        session.add(doc)
        await session.commit()

    result = {
        "parsed_id": doc.id,
        "policy_id": data.policy_id,
        "title": data.title,
        "extraction_method": extraction_method,
        "confidence": confidence,
        **rule_result,
    }

    doc_cache.set(cache_key, result)

    await event_bus.publish(EventMessage(
        event_type=EventType.DOCUMENT_PARSED,
        source_engine="document_understanding_engine",
        payload={
            "parsed_id": doc.id, "policy_id": data.policy_id,
            "extraction_method": extraction_method,
            "categories_found": rule_result.get("target_categories", []),
        },
    ))

    return ApiResponse(message="Document parsed", data=result)


@app.post("/documents/parse/batch", response_model=ApiResponse, tags=["Parse"])
async def parse_batch(data: BatchParseRequest):
    """Parse multiple documents in a batch."""
    results = []
    for doc in data.documents:
        rule_result = rule_based_extract(doc.text)
        results.append({
            "policy_id": doc.policy_id,
            "title": doc.title,
            **rule_result,
        })
    return ApiResponse(data=results, metadata={"batch_size": len(results)})


@app.get("/documents/parsed/{parsed_id}", response_model=ApiResponse, tags=["Query"])
async def get_parsed_document(parsed_id: str):
    """Get a previously parsed document by ID."""
    async with AsyncSessionLocal() as session:
        row = (await session.execute(
            select(ParsedDocument).where(ParsedDocument.id == parsed_id)
        )).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="Parsed document not found")
        return ApiResponse(data={
            "id": row.id, "policy_id": row.policy_id, "title": row.title,
            "eligibility_criteria": json.loads(row.eligibility_criteria or "[]"),
            "benefits": json.loads(row.benefits or "[]"),
            "required_documents": json.loads(row.required_documents or "[]"),
            "deadlines": json.loads(row.deadlines or "[]"),
            "income_limits": json.loads(row.income_limits or "{}"),
            "age_limits": json.loads(row.age_limits or "{}"),
            "target_categories": json.loads(row.target_categories or "[]"),
            "scheme_type": row.scheme_type,
            "confidence": row.confidence_score,
            "extraction_method": row.extraction_method,
        })


@app.get("/documents/by-policy/{policy_id}", response_model=ApiResponse, tags=["Query"])
async def get_by_policy(policy_id: str):
    """Get parsed documents for a specific policy."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(ParsedDocument)
            .where(ParsedDocument.policy_id == policy_id)
            .order_by(ParsedDocument.created_at.desc())
        )).scalars().all()
        return ApiResponse(data=[{
            "id": r.id, "title": r.title,
            "scheme_type": r.scheme_type,
            "target_categories": json.loads(r.target_categories or "[]"),
            "confidence": r.confidence_score,
            "method": r.extraction_method,
        } for r in rows])
