# Engine 7 — Neural Network Engine

> AI core using NVIDIA NIM — chat, RAG, intent classification, summarization, translation.

| Property | Value |
|----------|-------|
| **Port** | 8007 |
| **Folder** | `neural-network-engine/` |
| **Database Tables** | `conversation_logs` |
| **LLM** | Llama 3.1 70B Instruct via NVIDIA NIM |

## Run

```bash
uvicorn neural-network-engine.main:app --port 8007 --reload
```

Docs: http://localhost:8007/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/ai/chat` | Conversational AI about government schemes |
| POST | `/ai/rag` | RAG query with context passages |
| POST | `/ai/intent` | Intent classification & entity extraction |
| POST | `/ai/summarize` | Summarize scheme/policy text |
| POST | `/ai/translate` | Translate text between Indian languages |
| POST | `/ai/embeddings` | Generate text embeddings (NIM) |
| GET | `/ai/history/{user_id}` | Get conversation history |

## System Prompts

| Prompt | Purpose |
|--------|---------|
| `SYSTEM_PROMPT` | Main conversational AI — Indian government schemes expert |
| `RAG_PROMPT` | Retrieval-Augmented Generation with context chunks |
| `INTENT_PROMPT` | Classify intent: scheme_query, eligibility, complaint, general, greeting |
| `SUMMARY_PROMPT` | Summarize policy documents |
| `TRANSLATE_PROMPT` | Translate between Hindi, English, and regional languages |

## Intent Classification

Classifies user messages into actionable intents with keyword + NIM fallback:

- `scheme_query` — scheme information requests
- `eligibility` — eligibility checking
- `complaint` — grievance/complaint
- `deadline` — deadline inquiries
- `general` — general questions
- `greeting` — greetings

## Request Models

- `ChatRequest` — `user_id`, `message`, `language`, `context`
- `RAGRequest` — `query`, `context_passages` (list), `user_id`
- `IntentRequest` — `message` (str, required), `user_id` (optional)
- `SummarizeRequest` — `text`, `max_length`
- `TranslateRequest` — `text`, `source_lang`, `target_lang`
- `EmbeddingRequest` — `texts` (list)

## Gateway Route

`/api/v1/ai/*` → proxied from API Gateway (JWT auth required)

## Orchestrator Integration

This engine is the **most heavily used** engine across composite flows — it participates in **5 of 6** orchestrated pipelines:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **RAG Query** | `POST /api/v1/query` | Intent classification (Step 1) + RAG generation (Step 3) | Steps 1, 3 of 6 |
| **Eligibility Check** | `POST /api/v1/check-eligibility` | AI-generated explanation of eligibility results | Step 2 of 3 |
| **Simulation** | `POST /api/v1/simulate` | AI-generated explanation of delta impact | Step 2 of 3 |
| **Policy Ingestion** | `POST /api/v1/ingest-policy` | Generate embeddings for policy chunks | Step 4 of 7 |
| **Voice Query** | `POST /api/v1/voice-query` | Intent classification + response generation + translation | Steps 1, 2, 3 |

### Endpoints Called by Orchestrator

| Endpoint | Flows Using It |
|----------|---------------|
| `POST /ai/intent` | RAG Query, Voice Query |
| `POST /ai/rag` | RAG Query, Voice Query (scheme_query intent) |
| `POST /ai/chat` | RAG Query (fallback), Voice Query (default intent) |
| `POST /ai/summarize` | Eligibility Check, Simulation |
| `POST /ai/translate` | Voice Query (non-English) |
| `POST /ai/embeddings` | Policy Ingestion |

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | All AI endpoints across 5 composite flows |
| **Called by** | API Gateway (Proxy) | All `/ai/*` routes for direct access |
| **Depends on** | NVIDIA NIM API | Remote LLM inference (Llama 3.1 70B/8B) |
| **Fed by** | Vector Database (E6) | Context passages for RAG queries |
| **Feeds** | Vector Database (E6) | Embedding vectors during policy ingestion |
| **Publishes to** | Event Bus → E3, E13 | `AI_QUERY_PROCESSED` |

## Shared Module Dependencies

- `shared/config.py` — `settings` (NIM model IDs, API keys, port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`
- `shared/event_bus.py` — `event_bus`
- `shared/nvidia_client.py` — `nvidia_client` (chat completion, text generation, embeddings)
- `shared/utils.py` — `generate_id()`
- `shared/cache.py` — `LocalCache`
