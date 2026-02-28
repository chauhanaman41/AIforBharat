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
