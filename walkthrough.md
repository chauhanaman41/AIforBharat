# AIforBharat — Complete Platform Walkthrough

> **Personal Civic Operating System** — An AI-powered platform that connects Indian citizens with government schemes they're eligible for, using NVIDIA NIM, local-first architecture, and 21 specialized microservice engines.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Design Constraints](#design-constraints)
4. [Engine Directory](#engine-directory)
5. [Shared Foundation](#shared-foundation)
6. [Data Flow](#data-flow)
7. [Getting Started](#getting-started)
8. [Running Individual Engines](#running-individual-engines)
9. [Running the Full Platform](#running-the-full-platform)
10. [API Gateway Routing](#api-gateway-routing)
11. [Authentication Flow](#authentication-flow)
12. [Key Workflows](#key-workflows)
13. [Database & Storage](#database--storage)
14. [Event Bus Architecture](#event-bus-architecture)
15. [NVIDIA NIM Integration](#nvidia-nim-integration)
16. [Indian Languages Support](#indian-languages-support)
17. [Security & Privacy](#security--privacy)
18. [Port Reference](#port-reference)

---

## Architecture Overview

AIforBharat is a **21-engine microservice platform** where each engine handles a specific domain concern. All engines share a common foundation (`shared/`) and communicate via an **in-memory event bus**. The **API Gateway (Engine 9)** on port 8000 is the single entry point that proxies and authenticates requests to all downstream engines.

```
                        ┌────────────────────────────────┐
                        │       API Gateway (:8000)       │
                        │   Rate Limiting · JWT Auth      │
                        │   Request Logging · Routing     │
                        └──────────┬─────────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
    ┌──────▼──────┐         ┌──────▼──────┐         ┌──────▼──────┐
    │ Auth Layer  │         │  AI Layer   │         │ Data Layer  │
    │ Engine 1,2  │         │ Engine 7,20 │         │ Engine 3-6  │
    └──────┬──────┘         └──────┬──────┘         └──────┬──────┘
           │                       │                       │
    ┌──────▼──────┐         ┌──────▼──────┐         ┌──────▼──────┐
    │ Rules Layer │         │ Policy Layer│         │ Analytics   │
    │ Engine 8,15 │         │ Engine 11,21│         │ Engine 13   │
    │ Engine 16,19│         │ Engine 10   │         │ Engine 18   │
    └──────┬──────┘         └─────────────┘         └─────────────┘
           │
    ┌──────▼──────┐         ┌─────────────┐
    │ Aggregation │         │    UI BFF   │
    │ Engine 12,17│         │  Engine 14  │
    └─────────────┘         └─────────────┘
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.11 |
| **Web Framework** | FastAPI (async) |
| **ORM** | SQLAlchemy 2.0 (async mode) |
| **Database** | SQLite via `aiosqlite` (WAL mode) |
| **Validation** | Pydantic v2 + pydantic-settings |
| **AI / LLM** | NVIDIA NIM (OpenAI-compatible SDK) — Llama 3.1 70B/8B |
| **Embeddings** | NVIDIA `nv-embedqa-e5-v5` (1024-dim) |
| **Auth** | JWT (HS256) + bcrypt (12 rounds) |
| **Encryption** | AES-256-GCM via `cryptography` library |
| **Event Bus** | In-memory async pub/sub (replaces Kafka) |
| **File Storage** | Local filesystem (replaces S3/MinIO) |
| **Caching** | Two-tier: L1 in-memory + L2 file-based |

---

## Design Constraints

These constraints are **strictly enforced** across all 21 engines:

| Rule | Implementation |
|------|---------------|
| **Local-First** | SQLite DB, local filesystem, in-memory event bus — no cloud dependencies |
| **No AWS** | No S3, SQS, Lambda, DynamoDB, or any AWS service |
| **No DigiLocker** | Identity verification stubbed; trust score verification component = 0% |
| **No External Notifications** | OTP logged to console; no SMS/email/push services |
| **Data Caching** | Always check local cache before downloading any external data |
| **DPDP Compliance** | Right-to-erasure (cryptographic deletion) in Identity & Metadata engines |
| **Hash Chain Integrity** | Append-only event store with SHA-256 hash chains in Raw Data Store |

---

## Engine Directory

| # | Engine | Port | Folder | Purpose |
|---|--------|------|--------|---------|
| 1 | Login & Register | 8001 | `login-register-engine/` | User registration, JWT auth, OTP |
| 2 | Identity Engine | 8002 | `identity-engine/` | AES-256-GCM encrypted PII vault |
| 3 | Raw Data Store | 8003 | `raw-data-store/` | Append-only event store, hash chains |
| 4 | Metadata Engine | 8004 | `metadata-engine/` | Profile normalization & enrichment |
| 5 | Processed Metadata Store | 8005 | `processed-user-metadata-store/` | Persistent user metadata + eligibility cache |
| 6 | Vector Database | 8006 | `vector-database/` | In-memory vector index, cosine similarity |
| 7 | Neural Network Engine | 8007 | `neural-network-engine/` | AI chat, RAG, intent, translate via NIM |
| 8 | Anomaly Detection | 8008 | `anomaly-detection-engine/` | Rule-based anomaly scoring |
| 9 | API Gateway | 8000 | `api-gateway/` | Routing, rate limiting, JWT validation |
| 10 | Chunks Engine | 8010 | `chunks-engine/` | Document chunking (fixed/sentence/section) |
| 11 | Policy Fetching | 8011 | `policy-fetching-engine/` | Scheme data acquisition, 10 seed schemes |
| 12 | JSON User Info Generator | 8012 | `json-user-info-generator/` | Comprehensive profile assembly |
| 13 | Analytics Warehouse | 8013 | `analytics-warehouse/` | Platform analytics, funnels, metrics |
| 14 | Dashboard Interface | 8014 | `dashboard-interface/` | Backend-for-Frontend, widgets, search |
| 15 | Eligibility Rules Engine | 8015 | `eligibility-rules-engine/` | Deterministic scheme matching |
| 16 | Deadline Monitoring | 8016 | `deadline-monitoring-engine/` | Deadline tracking, urgency scoring |
| 17 | Simulation Engine | 8017 | `simulation-engine/` | What-if analysis, life event impact |
| 18 | Gov Data Sync | 8018 | `government-data-sync-engine/` | data.gov.in sync, census/NFHS data |
| 19 | Trust Scoring | 8019 | `trust-scoring-engine/` | Composite trust score (0-100) |
| 20 | Speech Interface | 8020 | `speech-interface-engine/` | Voice queries, 13 Indian languages |
| 21 | Document Understanding | 8021 | `document-understanding-engine/` | Policy parsing (rule + NIM hybrid) |

---

## Shared Foundation

All engines import from `shared/` — 7 modules providing cross-cutting concerns:

| Module | Purpose | Key Exports |
|--------|---------|-------------|
| `config.py` | Central settings (ports, API keys, paths) | `settings`, `ENGINE_URLS` |
| `models.py` | Pydantic models, enums | `ApiResponse`, `EventType`, `UserRole` |
| `database.py` | SQLAlchemy async engine + session | `Base`, `AsyncSessionLocal`, `init_db()` |
| `event_bus.py` | In-memory pub/sub | `event_bus.publish()`, `event_bus.subscribe()` |
| `cache.py` | Two-tier L1/L2 cache | `LocalCache`, `file_exists_locally()` |
| `nvidia_client.py` | NVIDIA NIM wrapper | `nvidia_client.chat_completion()`, `.generate_embedding()` |
| `utils.py` | Helpers (JWT, hashing, Indian data) | `create_access_token()`, `INDIAN_STATES`, `format_indian_currency()` |

---

## Data Flow

### User Registration → Eligibility Check

```
User signs up ──► Engine 1 (register, hash password, issue JWT)
                      │
                      ▼
               Engine 2 (encrypt PII in identity vault)
                      │
                      ▼
               Engine 4 (normalize metadata: age_group, income_bracket, life_stage)
                      │
                      ▼
               Engine 5 (persist processed metadata)
                      │
                      ▼
               Engine 15 (match against 10+ scheme rules → verdicts)
                      │
                      ▼
               Engine 12 (assemble full JSON profile)
                      │
                      ▼
               Engine 14 (serve to dashboard UI)
```

### Policy Ingestion Pipeline

```
Engine 11 (fetch policy from source / use seed data)
      │
      ▼
Engine 21 (parse: extract eligibility, benefits, deadlines)
      │
      ▼
Engine 10 (chunk into 512-token segments)
      │
      ▼
Engine 6 (embed chunks → vector index)
      │
      ▼
Engine 7 (RAG queries against indexed chunks)
```

### AI Query Flow

```
User question ──► Engine 20 (detect language, ASR if voice)
                      │
                      ▼
               Engine 7 (intent classification)
                      │
                      ├──► scheme_query → RAG with Engine 6 vectors
                      ├──► eligibility  → Engine 15 check
                      └──► general      → NIM chat completion
                              │
                              ▼
                        Engine 13 (log analytics event)
```

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **pip** (package manager)

### Install Dependencies

```bash
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic pydantic-settings
pip install python-jose[cryptography] passlib[bcrypt] bcrypt
pip install openai httpx python-multipart cryptography
```

Or from the project root:

```bash
pip install -r requirements.txt
```

### Project Structure

```
AIforBharat/
├── shared/                          # Shared foundation (7 modules)
│   ├── config.py                    # Central configuration
│   ├── models.py                    # Pydantic models & enums
│   ├── database.py                  # SQLAlchemy async setup
│   ├── event_bus.py                 # In-memory pub/sub
│   ├── cache.py                     # L1/L2 caching
│   ├── nvidia_client.py             # NVIDIA NIM client
│   └── utils.py                     # JWT, hashing, Indian helpers
├── api-gateway/                     # Engine 9 — entry point
│   ├── main.py
│   ├── routes.py
│   └── middleware.py
├── login-register-engine/           # Engine 1
│   └── main.py
├── identity-engine/                 # Engine 2
│   └── main.py
├── ...                              # Engines 3-8, 10-21
├── data/                            # Auto-created at runtime
│   ├── aiforbharat.db               # SQLite database
│   ├── cache/                       # L2 file cache
│   ├── raw-store/                   # Immutable event store
│   │   ├── hot/
│   │   ├── warm/
│   │   └── cold/
│   ├── gov-data/                    # Government datasets
│   └── audio/                       # Voice session recordings
└── walkthrough.md                   # ← You are here
```

---

## Running Individual Engines

Each engine is a standalone FastAPI app. Run any engine independently:

```bash
# Engine 1 — Login & Register
uvicorn login-register-engine.main:app --port 8001 --reload

# Engine 9 — API Gateway
uvicorn api-gateway.main:app --port 8000 --reload

# Engine 7 — Neural Network (AI)
uvicorn neural-network-engine.main:app --port 8007 --reload
```

Every engine exposes interactive API docs at `http://localhost:{PORT}/docs`.

---

## Running the Full Platform

Start all 21 engines (each in its own terminal or use a process manager):

```bash
# Terminal 1 — API Gateway (start this first)
uvicorn api-gateway.main:app --port 8000 --reload

# Terminal 2 — Auth engines
uvicorn login-register-engine.main:app --port 8001 --reload
uvicorn identity-engine.main:app --port 8002 --reload

# Terminal 3 — Data engines
uvicorn raw-data-store.main:app --port 8003 --reload
uvicorn metadata-engine.main:app --port 8004 --reload
uvicorn processed-user-metadata-store.main:app --port 8005 --reload
uvicorn vector-database.main:app --port 8006 --reload

# Terminal 4 — AI engines
uvicorn neural-network-engine.main:app --port 8007 --reload
uvicorn anomaly-detection-engine.main:app --port 8008 --reload

# Terminal 5 — Policy pipeline
uvicorn chunks-engine.main:app --port 8010 --reload
uvicorn policy-fetching-engine.main:app --port 8011 --reload
uvicorn document-understanding-engine.main:app --port 8021 --reload

# Terminal 6 — Business logic
uvicorn json-user-info-generator.main:app --port 8012 --reload
uvicorn eligibility-rules-engine.main:app --port 8015 --reload
uvicorn deadline-monitoring-engine.main:app --port 8016 --reload
uvicorn simulation-engine.main:app --port 8017 --reload

# Terminal 7 — Supporting engines
uvicorn analytics-warehouse.main:app --port 8013 --reload
uvicorn dashboard-interface.main:app --port 8014 --reload
uvicorn government-data-sync-engine.main:app --port 8018 --reload
uvicorn trust-scoring-engine.main:app --port 8019 --reload
uvicorn speech-interface-engine.main:app --port 8020 --reload
```

> **Tip**: Create a `start_all.ps1` PowerShell script or use `docker-compose` (future) to orchestrate all engines.

---

## API Gateway Routing

All client requests go through `http://localhost:8000/api/v1/`. The gateway proxies to downstream engines:

| Gateway Path | Target Engine | Port | Auth Required |
|-------------|---------------|------|:------------:|
| `/api/v1/auth/*` | Login & Register | 8001 | No |
| `/api/v1/identity/*` | Identity Engine | 8002 | Yes |
| `/api/v1/metadata/*` | Metadata Engine | 8004 | Yes |
| `/api/v1/eligibility/*` | Eligibility Rules | 8015 | Yes |
| `/api/v1/schemes/*` | Policy Fetching | 8011 | No |
| `/api/v1/policies/*` | Policy Fetching | 8011 | No |
| `/api/v1/simulate/*` | Simulation Engine | 8017 | Yes |
| `/api/v1/deadlines/*` | Deadline Monitoring | 8016 | Yes |
| `/api/v1/ai/*` | Neural Network | 8007 | Yes |
| `/api/v1/dashboard/*` | Dashboard Interface | 8014 | Yes |
| `/api/v1/documents/*` | Document Understanding | 8021 | Yes |
| `/api/v1/voice/*` | Speech Interface | 8020 | Yes |
| `/api/v1/analytics/*` | Analytics Warehouse | 8013 | Yes |
| `/api/v1/trust/*` | Trust Scoring | 8019 | Yes |
| `/api/v1/profile/*` | JSON User Info | 8012 | Yes |
| `/api/v1/debug/events` | Event Bus History | — | Yes |

---

## Authentication Flow

```
1. POST /api/v1/auth/register   →  Create account (phone + password)
2. POST /api/v1/auth/login      →  Get JWT access_token + refresh_token
3. Use header: Authorization: Bearer <access_token>
4. POST /api/v1/auth/token/refresh  →  Renew expired access token
```

JWT tokens are **HS256** signed with a random secret generated at startup. Access tokens expire in 30 minutes; refresh tokens in 7 days.

---

## Key Workflows

### 1. Check Scheme Eligibility

```bash
POST /api/v1/eligibility/check
{
  "user_profile": {
    "age": 35,
    "annual_income": 180000,
    "state": "Bihar",
    "occupation": "farmer",
    "land_holding_acres": 3.5,
    "caste_category": "OBC"
  }
}
# Returns: verdicts for PM-KISAN, PMAY, PMJAY, Ujjwala, etc.
```

### 2. What-If Simulation

```bash
POST /api/v1/simulate/what-if
{
  "user_id": "usr_abc123",
  "current_profile": { "age": 28, "annual_income": 400000, "occupation": "salaried" },
  "changes": { "annual_income": 180000, "occupation": "farmer" },
  "scenario_type": "custom"
}
# Returns: schemes gained/lost by changing profile
```

### 3. AI Chat (Hindi)

```bash
POST /api/v1/ai/chat
{
  "user_id": "usr_abc123",
  "message": "मुझे किसानों के लिए सरकारी योजनाओं के बारे में बताइए",
  "language": "hindi"
}
# Returns: AI response about farmer schemes in Hindi
```

### 4. Voice Query

```bash
POST /api/v1/voice/query
{
  "text": "पीएम किसान योजना के लिए कैसे आवेदन करें",
  "language": "hindi"
}
# Returns: AI response + detected language
```

---

## Database & Storage

### SQLite Database

Single database file: `data/aiforbharat.db` (auto-created at startup)

| Table | Engine | Purpose |
|-------|--------|---------|
| `users` | Engine 1 | User accounts |
| `otp_records` | Engine 1 | OTP log |
| `refresh_tokens` | Engine 1 | JWT refresh tokens |
| `identity_vaults` | Engine 2 | AES-encrypted PII |
| `user_metadata` | Engine 5 | Processed profiles |
| `user_derived_attributes` | Engine 5 | Computed fields |
| `user_eligibility_cache` | Engine 5 | Cached verdicts |
| `user_risk_scores` | Engine 5 | Risk assessments |
| `vector_records` | Engine 6 | Embeddings + metadata |
| `conversation_logs` | Engine 7 | AI chat history |
| `anomaly_records` | Engine 8 | Detected anomalies |
| `document_chunks` | Engine 10 | Chunked text |
| `fetched_documents` | Engine 11 | Policy documents |
| `source_configs` | Engine 11 | Data sources |
| `generated_profiles` | Engine 12 | Assembled profiles |
| `analytics_events` | Engine 13 | Event log |
| `metric_snapshots` | Engine 13 | Time-series metrics |
| `funnel_steps` | Engine 13 | Funnel analysis |
| `dashboard_preferences` | Engine 14 | User UI preferences |
| `eligibility_rules` | Engine 15 | Scheme rules |
| `eligibility_results` | Engine 15 | Check results |
| `scheme_deadlines` | Engine 16 | Deadline records |
| `user_deadline_alerts` | Engine 16 | User alerts |
| `simulation_records` | Engine 17 | What-if results |
| `synced_datasets` | Engine 18 | Gov data catalog |
| `gov_data_records` | Engine 18 | Census/NFHS data |
| `trust_score_records` | Engine 19 | Trust scores |
| `voice_sessions` | Engine 20 | Speech sessions |
| `parsed_documents` | Engine 21 | Extracted fields |

### Local Filesystem

```
data/
├── aiforbharat.db           # SQLite database (all tables)
├── cache/                   # L2 file cache (JSON per key)
├── raw-store/               # Immutable event log
│   ├── hot/YYYY/MM/DD/      # Recent events (JSON files)
│   ├── warm/                # Aged events
│   └── cold/                # Archived events
├── gov-data/                # Government datasets (JSON)
└── audio/                   # Voice recordings (WAV)
```

---

## Event Bus Architecture

The `LocalEventBus` replaces Apache Kafka for local development. All engines publish events that other engines can subscribe to:

```python
# Publishing (any engine)
await event_bus.publish(EventMessage(
    event_type=EventType.USER_REGISTERED,
    source="login_register_engine",
    data={"user_id": "usr_123", "phone": "9876543210"}
))

# Subscribing (any engine)
async def on_user_registered(msg):
    print(f"New user: {msg['data']['user_id']}")

event_bus.subscribe("USER_REGISTERED", on_user_registered)

# Wildcard — subscribe to ALL events
event_bus.subscribe("*", analytics_handler)
```

### Event Types (30+)

Auth: `USER_REGISTERED`, `LOGIN_SUCCESS`, `LOGIN_FAILED`, `TOKEN_REFRESHED`, `LOGOUT`
Identity: `IDENTITY_CREATED`, `IDENTITY_VERIFIED`, `IDENTITY_DELETED`, `DATA_EXPORTED`
Policy: `POLICY_FETCHED`, `POLICY_UPDATED`, `POLICY_AMENDED`
AI: `AI_RESPONSE_GENERATED`, `ANOMALY_DETECTED`, `TRUST_SCORE_COMPUTED`
Data: `RAW_DATA_STORED`, `INTEGRITY_VIOLATION`, `GOV_DATA_SYNCED`

---

## NVIDIA NIM Integration

The platform uses NVIDIA NIM via the OpenAI-compatible Python SDK:

| Model | ID | Use Case |
|-------|----|----------|
| Llama 3.1 70B Instruct | `meta/llama-3.1-70b-instruct` | Chat, RAG, document parsing |
| Llama 3.1 8B Instruct | `meta/llama-3.1-8b-instruct` | Intent classification, summaries |
| NV EmbedQA E5 v5 | `nvidia/nv-embedqa-e5-v5` | Text embeddings (1024-dim) |
| Rerank QA Mistral 4B | `nvidia/rerank-qa-mistral-4b` | Search result reranking |

All NIM calls go through `shared/nvidia_client.py` which provides retry logic and graceful fallbacks (hash-based embeddings if API is unreachable).

---

## Indian Languages Support

| Language | Code | Script Detection |
|----------|------|:---------------:|
| Hindi | hi-IN | ✓ (Devanagari) |
| English | en-IN | ✓ (Latin) |
| Bengali | bn-IN | ✓ |
| Tamil | ta-IN | ✓ |
| Telugu | te-IN | ✓ |
| Marathi | mr-IN | ✓ |
| Gujarati | gu-IN | ✓ |
| Kannada | kn-IN | ✓ |
| Malayalam | ml-IN | ✓ |
| Punjabi | pa-IN | ✓ |
| Odia | or-IN | ✓ |
| Assamese | as-IN | ✓ |
| Urdu | ur-IN | ✓ |

Language detection uses **Unicode script range analysis** in the Speech Interface Engine. The Neural Network Engine can translate between any of these languages via NIM.

---

## Security & Privacy

| Feature | Implementation |
|---------|---------------|
| **Password Hashing** | bcrypt (12 rounds) |
| **PII Encryption** | AES-256-GCM per-field encryption in Identity Engine |
| **JWT Authentication** | HS256, 30-min access / 7-day refresh |
| **Rate Limiting** | Token bucket: 100 req/min per IP |
| **DPDP Compliance** | Right-to-erasure via cryptographic deletion |
| **Data Export** | Full data export endpoint (Engine 2) |
| **Audit Trail** | Every event stored in hash-chained append-only log |
| **Input Validation** | Pydantic v2 strict validation on all endpoints |

---

## Port Reference

| Port | Engine |
|------|--------|
| 8000 | API Gateway |
| 8001 | Login & Register |
| 8002 | Identity Engine |
| 8003 | Raw Data Store |
| 8004 | Metadata Engine |
| 8005 | Processed Metadata Store |
| 8006 | Vector Database |
| 8007 | Neural Network Engine |
| 8008 | Anomaly Detection |
| 8010 | Chunks Engine |
| 8011 | Policy Fetching |
| 8012 | JSON User Info Generator |
| 8013 | Analytics Warehouse |
| 8014 | Dashboard Interface |
| 8015 | Eligibility Rules Engine |
| 8016 | Deadline Monitoring |
| 8017 | Simulation Engine |
| 8018 | Gov Data Sync |
| 8019 | Trust Scoring |
| 8020 | Speech Interface |
| 8021 | Document Understanding |

> Port 8009 is intentionally unused.

---

## Seed Data

The platform ships with pre-loaded seed data for immediate local testing:

- **10 Government Schemes**: PM-KISAN, PMAY, Ayushman Bharat (PMJAY), PM Ujjwala, PM MUDRA, PMSBY, PMJJBY, Sukanya Samriddhi, NPS, SC/ST Post-Matric Scholarship
- **5 Government Datasets**: NFHS-5 District Data, Census 2011, SDG India Index, Poverty Headcount Ratios, Scheme Beneficiary Statistics
- **5 Scheme Deadlines**: PM-KISAN, PMAY, Sukanya Samriddhi, SC/ST Scholarship, PM MUDRA
- **10 Built-in Eligibility Rules**: One rule set per seed scheme with age/income/occupation/state criteria
- **8 Simulation Scheme Rules**: With benefit values for what-if analysis

---

*Built with ❤️ for Bharat — empowering every citizen to discover and access the government benefits they deserve.*
