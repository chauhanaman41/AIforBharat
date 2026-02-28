"""
AIforBharat — Speech Interface Engine (Engine 20)
==================================================
Voice-based interaction for Indian users. Uses NVIDIA NIM for
speech-to-text (ASR) and text-to-speech (TTS). Supports Hindi,
English, and regional languages. Provides transliteration and
language detection. Routes voice queries to Neural Network Engine.

Port: 8020
"""

import logging, time, os, sys, json, re, base64
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.utils import generate_id, INDIAN_LANGUAGES
from shared.nvidia_client import nvidia_client
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("speech_interface")
START_TIME = time.time()

AUDIO_DIR = Path(settings.LOCAL_DATA_DIR) / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
speech_cache = LocalCache(namespace="speech", ttl=1800)

# Language codes mapping for Indian languages
LANGUAGE_MAP = {
    "hindi": "hi-IN", "english": "en-IN", "bengali": "bn-IN",
    "tamil": "ta-IN", "telugu": "te-IN", "marathi": "mr-IN",
    "gujarati": "gu-IN", "kannada": "kn-IN", "malayalam": "ml-IN",
    "punjabi": "pa-IN", "odia": "or-IN", "assamese": "as-IN",
    "urdu": "ur-IN",
}

# Unicode script ranges for language detection
SCRIPT_PATTERNS = {
    "hindi": re.compile(r'[\u0900-\u097F]'),
    "bengali": re.compile(r'[\u0980-\u09FF]'),
    "tamil": re.compile(r'[\u0B80-\u0BFF]'),
    "telugu": re.compile(r'[\u0C00-\u0C7F]'),
    "kannada": re.compile(r'[\u0C80-\u0CFF]'),
    "malayalam": re.compile(r'[\u0D00-\u0D7F]'),
    "gujarati": re.compile(r'[\u0A80-\u0AFF]'),
    "punjabi": re.compile(r'[\u0A00-\u0A7F]'),
    "odia": re.compile(r'[\u0B00-\u0B7F]'),
    "urdu": re.compile(r'[\u0600-\u06FF]'),
}


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class VoiceSession(Base):
    __tablename__ = "voice_sessions"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, index=True)
    language = Column(String, default="hindi")
    audio_path = Column(Text)
    transcript = Column(Text)
    response_text = Column(Text)
    response_audio_path = Column(Text)
    duration_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Schemas ───────────────────────────────────────────────────────────────────

class TextToSpeechRequest(BaseModel):
    text: str
    language: str = "hindi"
    user_id: Optional[str] = None


class SpeechToTextResult(BaseModel):
    transcript: str
    language: str
    confidence: float


class VoiceQueryRequest(BaseModel):
    text: str
    language: str = "hindi"
    user_id: Optional[str] = None


class LanguageDetectRequest(BaseModel):
    text: str


class TransliterateRequest(BaseModel):
    text: str
    source_lang: str = "english"
    target_lang: str = "hindi"


# ── Helper Functions ──────────────────────────────────────────────────────────

def detect_language(text: str) -> str:
    """Detect language from text using Unicode script analysis."""
    for lang, pattern in SCRIPT_PATTERNS.items():
        matches = len(pattern.findall(text))
        if matches > len(text) * 0.3:
            return lang
    if re.search(r'[a-zA-Z]', text):
        return "english"
    return "hindi"  # Default


async def _simulate_asr(audio_bytes: bytes, language: str) -> dict:
    """
    Simulate ASR using NVIDIA NIM.
    In production, would use NIM ASR endpoint.
    Currently returns a stub for local-first operation.
    """
    # In production: send audio_bytes to NVIDIA Riva/NIM ASR
    logger.info(f"ASR requested for language={language}, audio_size={len(audio_bytes)} bytes")
    return {
        "transcript": "[ASR pending — NVIDIA Riva integration required for production]",
        "language": language,
        "confidence": 0.0,
    }


async def _simulate_tts(text: str, language: str) -> Optional[bytes]:
    """
    Simulate TTS using NVIDIA NIM.
    In production, would use NIM TTS endpoint.
    Currently generates a placeholder.
    """
    logger.info(f"TTS requested: language={language}, text_length={len(text)}")
    # Placeholder: return empty bytes (real implementation uses NIM TTS)
    return None


async def _process_voice_query(text: str, language: str, user_id: Optional[str]) -> str:
    """Send text to Neural Network Engine for processing, with language context."""
    prompt = text
    if language != "english":
        prompt = f"[User is speaking in {language}] {text}"

    try:
        response = await nvidia_client.generate_text(
            prompt=prompt,
            system_prompt=(
                "You are a helpful Indian government schemes assistant. "
                f"The user is communicating in {language}. "
                "Respond in the same language. Be concise and helpful."
            ),
            max_tokens=300,
        )
        return response
    except Exception as e:
        logger.error(f"NIM query failed: {e}")
        if language == "hindi":
            return "माफ़ कीजिए, अभी AI सेवा उपलब्ध नहीं है। कृपया बाद में प्रयास करें।"
        return "Sorry, the AI service is currently unavailable. Please try again later."


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Speech Interface Engine starting...")
    await init_db()
    yield

app = FastAPI(title="AIforBharat Speech Interface Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="speech_interface_engine", uptime_seconds=time.time() - START_TIME)


@app.post("/speech/stt", response_model=ApiResponse, tags=["Speech-to-Text"])
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = Form("hindi"),
):
    """Convert speech audio to text."""
    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Save audio locally
    audio_id = generate_id()
    audio_path = AUDIO_DIR / f"{audio_id}.wav"
    audio_path.write_bytes(audio_bytes)

    result = await _simulate_asr(audio_bytes, language)

    async with AsyncSessionLocal() as session:
        session.add(VoiceSession(
            id=audio_id, language=language,
            audio_path=str(audio_path), transcript=result["transcript"],
            duration_seconds=len(audio_bytes) / 32000,  # rough estimate
        ))
        await session.commit()

    return ApiResponse(data=result)


@app.post("/speech/tts", response_model=ApiResponse, tags=["Text-to-Speech"])
async def text_to_speech(data: TextToSpeechRequest):
    """Convert text to speech audio."""
    audio_bytes = await _simulate_tts(data.text, data.language)

    audio_id = generate_id()
    audio_path = None
    if audio_bytes:
        audio_path = AUDIO_DIR / f"tts_{audio_id}.wav"
        audio_path.write_bytes(audio_bytes)

    async with AsyncSessionLocal() as session:
        session.add(VoiceSession(
            id=audio_id, user_id=data.user_id,
            language=data.language, response_text=data.text,
            response_audio_path=str(audio_path) if audio_path else None,
        ))
        await session.commit()

    return ApiResponse(
        message="TTS generated" if audio_bytes else "TTS pending (NIM Riva required)",
        data={
            "session_id": audio_id,
            "audio_available": audio_bytes is not None,
            "text": data.text,
            "language": data.language,
        },
    )


@app.post("/speech/query", response_model=ApiResponse, tags=["Voice Query"])
async def voice_query(data: VoiceQueryRequest):
    """Process a text query (from voice) and return AI response."""
    detected_lang = detect_language(data.text)
    language = data.language if data.language != "hindi" else detected_lang

    response_text = await _process_voice_query(data.text, language, data.user_id)

    session_id = generate_id()
    async with AsyncSessionLocal() as session:
        session.add(VoiceSession(
            id=session_id, user_id=data.user_id,
            language=language, transcript=data.text,
            response_text=response_text,
        ))
        await session.commit()

    await event_bus.publish(EventMessage(
        event_type=EventType.AI_QUERY_PROCESSED,
        source="speech_interface_engine",
        data={"user_id": data.user_id, "language": language, "query_length": len(data.text)},
    ))

    return ApiResponse(data={
        "session_id": session_id,
        "query": data.text,
        "response": response_text,
        "language": language,
        "detected_language": detected_lang,
    })


@app.post("/speech/detect-language", response_model=ApiResponse, tags=["Language"])
async def detect_language_endpoint(data: LanguageDetectRequest):
    """Detect the language of input text."""
    lang = detect_language(data.text)
    lang_code = LANGUAGE_MAP.get(lang, "en-IN")
    return ApiResponse(data={
        "language": lang,
        "language_code": lang_code,
        "script_detected": lang not in ("english",),
    })


@app.post("/speech/transliterate", response_model=ApiResponse, tags=["Language"])
async def transliterate(data: TransliterateRequest):
    """Transliterate text between scripts using NIM."""
    try:
        result = await nvidia_client.generate_text(
            prompt=f"Transliterate the following {data.source_lang} text to {data.target_lang} script. Return ONLY the transliterated text:\n\n{data.text}",
            max_tokens=200,
        )
        return ApiResponse(data={
            "original": data.text,
            "transliterated": result.strip(),
            "source": data.source_lang,
            "target": data.target_lang,
        })
    except Exception as e:
        logger.error(f"Transliteration failed: {e}")
        return ApiResponse(message="Transliteration unavailable", data={
            "original": data.text, "transliterated": data.text,
        })


@app.get("/speech/languages", response_model=ApiResponse, tags=["Language"])
async def supported_languages():
    """List supported Indian languages."""
    return ApiResponse(data=[
        {"name": name, "code": code}
        for name, code in LANGUAGE_MAP.items()
    ])


@app.get("/speech/sessions", response_model=ApiResponse, tags=["Sessions"])
async def list_sessions(user_id: Optional[str] = None, limit: int = 20):
    """List voice sessions."""
    async with AsyncSessionLocal() as session:
        query = select(VoiceSession).order_by(VoiceSession.created_at.desc())
        if user_id:
            query = query.where(VoiceSession.user_id == user_id)
        rows = (await session.execute(query.limit(limit))).scalars().all()
        return ApiResponse(data=[{
            "id": r.id, "user_id": r.user_id,
            "language": r.language, "transcript": r.transcript,
            "response": r.response_text,
            "created_at": r.created_at.isoformat(),
        } for r in rows])
