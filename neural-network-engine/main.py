"""
AIforBharat — Neural Network Engine (Engine 7)
================================================
AI core using NVIDIA NIM for natural language processing:
- Conversational AI for scheme queries
- RAG (Retrieval-Augmented Generation) over policy documents
- Summarization, translation, Q&A
- Intent classification and entity extraction

Port: 8007
"""

import logging, time, os, sys, json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.config import settings
from shared.database import Base, AsyncSessionLocal, init_db
from shared.models import ApiResponse, HealthResponse, EventMessage, EventType
from shared.event_bus import event_bus
from shared.nvidia_client import nvidia_client, NIMUnavailableError, NIM_DEGRADED_MESSAGE
from shared.utils import generate_id
from shared.cache import LocalCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("neural_network_engine")
START_TIME = time.time()
ai_cache = LocalCache(namespace="neural_net", ttl=900)


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

class ConversationLog(Base):
    __tablename__ = "conversation_logs"
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, index=True)
    session_id = Column(String, index=True)
    role = Column(String)          # user, assistant, system
    content = Column(Text)
    intent = Column(String)
    tokens_used = Column(Integer, default=0)
    model_used = Column(String)
    latency_ms = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── System Prompts ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI assistant for AIforBharat, a platform that helps Indian citizens discover and access government schemes and welfare programs.

Your role:
- Help users understand their eligibility for government schemes
- Explain scheme benefits, deadlines, and application processes
- Answer questions about Indian government welfare programs
- Provide information in a simple, empathetic manner
- Support multilingual queries (primarily Hindi and English)

Important rules:
- Always be accurate about scheme details
- If unsure, say so rather than provide wrong information
- Be sensitive to the user's socio-economic context
- Provide actionable next steps when possible
- Never ask for sensitive documents like Aadhaar numbers through chat
- Use simple language, avoid bureaucratic jargon"""

RAG_PROMPT = """You are an AI assistant. Use the following context passages from government scheme documents to answer the user's question. If the context doesn't contain enough information, say so clearly.

Context:
{context}

User's question: {question}

Provide a clear, helpful answer based on the context. Include specific details like amounts, eligibility criteria, and deadlines when available."""

INTENT_PROMPT = """Classify the user's intent from their message. Return a JSON object with:
- intent: one of [scheme_query, eligibility_check, application_help, deadline_query, benefit_calculation, general_question, greeting, complaint, feedback]
- entities: extracted entities like scheme_name, state, income, category, age
- confidence: 0.0 to 1.0
- language: detected language (en, hi, ta, te, bn, mr, gu, kn, ml, pa, or)

User message: "{message}"

Return ONLY valid JSON."""

SUMMARY_PROMPT = """Summarize the following government scheme information in simple language that a common citizen can understand. Keep it under 200 words. Include:
1. What the scheme provides
2. Who is eligible
3. How to apply

Text:
{text}"""

TRANSLATE_PROMPT = """Translate the following text from {source_lang} to {target_lang}. Maintain the meaning and tone. If it contains government scheme terminology, use commonly understood terms.

Text: {text}

Translation:"""


# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    message: str
    context: Optional[List[dict]] = None     # Previous messages [{role, content}]
    max_tokens: int = 1000
    temperature: float = 0.7


class RAGRequest(BaseModel):
    user_id: str
    question: str
    context_passages: List[str]    # Retrieved chunks from Vector DB
    max_tokens: int = 1000


class IntentRequest(BaseModel):
    message: str
    user_id: Optional[str] = None


class SummarizeRequest(BaseModel):
    text: str
    max_length: int = 200


class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "hi"


class EmbeddingRequest(BaseModel):
    texts: List[str]


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Neural Network Engine starting...")
    await init_db()
    yield

app = FastAPI(title="AIforBharat Neural Network Engine", version=settings.APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(engine="neural_network_engine", uptime_seconds=time.time() - START_TIME)


@app.post("/ai/chat", response_model=ApiResponse, tags=["Chat"])
async def chat(data: ChatRequest):
    """
    Conversational AI endpoint for scheme-related queries.
    Uses NVIDIA NIM for response generation.
    
    Input: User message + optional conversation history
    Output: AI response with intent classification
    """
    session_id = data.session_id or generate_id()
    start = time.time()

    # Build messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if data.context:
        for msg in data.context[-10:]:  # Last 10 messages
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": data.message})

    try:
        response = await nvidia_client.chat_completion(
            messages=messages,
            max_tokens=data.max_tokens,
            temperature=data.temperature,
        )
    except NIMUnavailableError:
        logger.warning("LLM circuit breaker OPEN — returning degraded chat response")
        response = NIM_DEGRADED_MESSAGE
    except Exception as e:
        logger.error(f"NIM chat failed: {e}")
        response = "I apologize, but I'm having trouble connecting to my AI backend right now. Please try again in a moment, or I can help you with basic scheme information."

    latency_ms = (time.time() - start) * 1000

    # Log conversation
    async with AsyncSessionLocal() as session:
        session.add(ConversationLog(
            id=generate_id(), user_id=data.user_id, session_id=session_id,
            role="user", content=data.message,
        ))
        session.add(ConversationLog(
            id=generate_id(), user_id=data.user_id, session_id=session_id,
            role="assistant", content=response, latency_ms=latency_ms,
            model_used=settings.NIM_MODEL_8B,
        ))
        await session.commit()

    await event_bus.publish(EventMessage(
        event_type=EventType.AI_QUERY_PROCESSED,
        source_engine="neural_network_engine",
        user_id=data.user_id,
        payload={"session_id": session_id, "latency_ms": round(latency_ms)},
    ))

    return ApiResponse(data={
        "response": response,
        "session_id": session_id,
        "latency_ms": round(latency_ms, 1),
    })


@app.post("/ai/rag", response_model=ApiResponse, tags=["RAG"])
async def rag_query(data: RAGRequest):
    """
    RAG (Retrieval-Augmented Generation) query.
    Takes retrieved context passages and generates an answer.
    
    Input: Question + context passages from Vector DB search
    Output: Contextualized answer
    """
    context = "\n\n---\n\n".join(data.context_passages[:5])
    prompt = RAG_PROMPT.format(context=context, question=data.question)

    try:
        response = await nvidia_client.generate_text(
            prompt, max_tokens=data.max_tokens, temperature=0.3,
        )
    except NIMUnavailableError:
        logger.warning("RAG: LLM circuit breaker open")
        response = NIM_DEGRADED_MESSAGE
    except Exception as e:
        logger.error(f"RAG failed: {e}")
        response = "I couldn't process your query right now. The context suggests checking the relevant scheme documentation directly."

    return ApiResponse(data={
        "answer": response,
        "context_used": len(data.context_passages),
        "question": data.question,
    })


@app.post("/ai/intent", response_model=ApiResponse, tags=["NLP"])
async def classify_intent(data: IntentRequest):
    """
    Classify user intent and extract entities from a message.
    
    Input: User message
    Output: Intent, entities, confidence, language
    """
    cache_key = f"intent:{data.message[:100]}"
    cached = ai_cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    try:
        response = await nvidia_client.generate_text(
            INTENT_PROMPT.format(message=data.message),
            max_tokens=300, temperature=0.1,
        )
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"intent": "general_question", "entities": {}, "confidence": 0.5, "language": "en"}
    except NIMUnavailableError:
        logger.warning("Intent: LLM circuit breaker open")
        result = {"intent": "scheme_query", "entities": {}, "confidence": 0.3, "language": "en", "degraded": True}
        ai_cache.set(cache_key, result)
        return ApiResponse(data=result, metadata={"degraded": True})
    except Exception as e:
        logger.warning(f"Intent classification failed: {e}")
        # Fallback: keyword-based classification
        msg_lower = data.message.lower()
        if any(k in msg_lower for k in ["eligible", "qualify", "can i get"]):
            intent = "eligibility_check"
        elif any(k in msg_lower for k in ["deadline", "last date", "when"]):
            intent = "deadline_query"
        elif any(k in msg_lower for k in ["how to apply", "apply", "application"]):
            intent = "application_help"
        elif any(k in msg_lower for k in ["hello", "hi", "namaste"]):
            intent = "greeting"
        else:
            intent = "scheme_query"
        result = {"intent": intent, "entities": {}, "confidence": 0.6, "language": "en"}

    ai_cache.set(cache_key, result)
    return ApiResponse(data=result)


@app.post("/ai/summarize", response_model=ApiResponse, tags=["NLP"])
async def summarize(data: SummarizeRequest):
    """Summarize scheme text in simple language."""
    cache_key = f"summary:{hash(data.text[:200])}"
    cached = ai_cache.get(cache_key)
    if cached:
        return ApiResponse(data=cached, metadata={"source": "cache"})

    try:
        response = await nvidia_client.generate_text(
            SUMMARY_PROMPT.format(text=data.text[:3000]),
            max_tokens=500, temperature=0.3,
        )
    except NIMUnavailableError:
        logger.warning("Summarize: LLM circuit breaker open")
        response = data.text[:500] + "..."
    except Exception as e:
        logger.warning(f"Summarization failed: {e}")
        response = data.text[:500] + "..."

    result = {"summary": response, "original_length": len(data.text)}
    ai_cache.set(cache_key, result)
    return ApiResponse(data=result)


@app.post("/ai/translate", response_model=ApiResponse, tags=["NLP"])
async def translate(data: TranslateRequest):
    """Translate text between languages."""
    try:
        response = await nvidia_client.generate_text(
            TRANSLATE_PROMPT.format(
                source_lang=data.source_lang, target_lang=data.target_lang,
                text=data.text,
            ),
            max_tokens=1000, temperature=0.2,
        )
    except NIMUnavailableError:
        logger.warning("Translate: LLM circuit breaker open")
        response = data.text  # Fallback: return original
    except Exception as e:
        logger.warning(f"Translation failed: {e}")
        response = data.text  # Fallback: return original

    return ApiResponse(data={
        "original": data.text,
        "translated": response,
        "source_lang": data.source_lang,
        "target_lang": data.target_lang,
    })


@app.post("/ai/embeddings", response_model=ApiResponse, tags=["Embeddings"])
async def generate_embeddings(data: EmbeddingRequest):
    """Generate embeddings for text using NVIDIA NIM."""
    try:
        embeddings = await nvidia_client.generate_embeddings_batch(data.texts)
        return ApiResponse(data={
            "embeddings": embeddings,
            "dimensions": len(embeddings[0]) if embeddings else 0,
            "count": len(embeddings),
        })
    except NIMUnavailableError:
        logger.warning("Embeddings: LLM circuit breaker open")
        raise HTTPException(status_code=503, detail=NIM_DEGRADED_MESSAGE)
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {e}")


@app.get("/ai/history/{user_id}", response_model=ApiResponse, tags=["History"])
async def get_chat_history(user_id: str, session_id: Optional[str] = None, limit: int = 50):
    """Get conversation history for a user."""
    async with AsyncSessionLocal() as session:
        query = select(ConversationLog).where(ConversationLog.user_id == user_id)
        if session_id:
            query = query.where(ConversationLog.session_id == session_id)
        query = query.order_by(ConversationLog.created_at.desc()).limit(limit)

        rows = (await session.execute(query)).scalars().all()
        return ApiResponse(data=[{
            "role": r.role, "content": r.content,
            "session_id": r.session_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in reversed(rows)])  # Chronological order
