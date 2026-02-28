# AIforBharat — Orchestra Formation & Engine Connectivity Plan

> **Date:** February 28, 2026
> **Author:** Senior Distributed Systems Architect
> **Status:** Verified — Integration Testing Passed
> **Scope:** Integration and orchestration only. No engine redesign.

---

## Preamble: Key Architectural Observations

> **Update (Feb 28 - Guardrails):** All 21 engines have now been successfully tested via the `test_orchestration.py` suite. The architecture has been hardened with a set of Minimal Guardrails, including rate-limiting (Burst & RPM), an LLM Circuit Breaker (E7), and structured `NIMUnavailableError` fallback handlers. Re-running `test_orchestration.py` confirmed that the orchestrator elegantly handles E7 failures without dropping user requests. Furthermore, every engine's `README.md` has been updated with detailed "Orchestrator Integration" sections.

Before defining the orchestration, three critical facts about the current system must be stated clearly — they shape every decision that follows.

### Observation 1: Hub-and-Spoke Topology
Only the **API Gateway** (`api-gateway/routes.py`) makes cross-engine HTTP calls via `httpx.AsyncClient`. All other 20 engines are **leaf nodes** — they serve requests and never call sibling engines over HTTP. This is a strength, not a limitation. It means there are **zero circular dependencies** in the current system.

### Observation 2: In-Process Event Bus Isolation
The `LocalEventBus` in `shared/event_bus.py` is an **in-memory singleton per Python process**. Since each engine runs as a separate `uvicorn` process, events published in Engine A are **invisible to Engine B**. Three engines subscribe to events (`raw_data_store` on `*`, `chunks_engine` on `document.*`, `analytics_warehouse` on `*`), but these subscriptions only fire for events published within their own process. **Cross-engine events do not propagate today.**

### Observation 3: Shared SQLite as De Facto IPC
All 21 engines connect to the same `data/aiforbharat.db` via SQLAlchemy (async). This shared database is the **actual data exchange mechanism** — one engine writes a row, another engine reads it. This works for MVP but creates write contention under load due to SQLite's single-writer lock.

These three facts mean the orchestration layer must be a **request choreographer** that chains HTTP calls through the gateway, not an event-driven reactor.

---

## 1️⃣ Updated System Topology

### Engine Registry (21 Engines + 1 Shared Foundation)

```
┌─────────────────────────────────────────────────────────────────┐
│                     LAYER 1: USER INTERACTION                   │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐ │
│  │ Dashboard Interface  │  │    Speech Interface Engine       │ │
│  │     (E14 : 8014)     │  │        (E20 : 8020)             │ │
│  └──────────────────────┘  └──────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                  LAYER 2: API & ORCHESTRATION                   │
│  ┌───────────────┐ ┌────────────────┐ ┌──────────────────────┐ │
│  │  API Gateway  │ │ Login/Register │ │  Identity Engine     │ │
│  │ (E0 : 8000)   │ │  (E1 : 8001)   │ │   (E2 : 8002)       │ │
│  └───────────────┘ └────────────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                    LAYER 3: INTELLIGENCE                        │
│  ┌──────────────────┐ ┌───────────────────────┐                │
│  │ Neural Network   │ │ Doc Understanding     │                │
│  │  (E7 : 8007)     │ │  (E21 : 8021)         │                │
│  ├──────────────────┤ ├───────────────────────┤                │
│  │ Metadata Engine  │ │ JSON User Info Gen    │                │
│  │  (E4 : 8004)     │ │  (E12 : 8012)         │                │
│  ├──────────────────┤ ├───────────────────────┤                │
│  │ Trust Scoring    │ │                       │                │
│  │  (E19 : 8019)    │ │                       │                │
│  └──────────────────┘ └───────────────────────┘                │
├─────────────────────────────────────────────────────────────────┤
│                  LAYER 4: DETERMINISTIC LOGIC                   │
│  ┌──────────────────┐ ┌──────────────────┐ ┌────────────────┐ │
│  │ Eligibility      │ │ Simulation       │ │ Deadline       │ │
│  │ Rules (E15:8015) │ │ (E17 : 8017)     │ │ (E16 : 8016)   │ │
│  ├──────────────────┤ └──────────────────┘ └────────────────┘ │
│  │ Anomaly Detection│                                         │
│  │ (E8 : 8008)      │                                         │
│  └──────────────────┘                                         │
├─────────────────────────────────────────────────────────────────┤
│                       LAYER 5: DATA                             │
│  ┌──────────────────┐ ┌──────────────────┐ ┌────────────────┐ │
│  │ Policy Fetching  │ │ Raw Data Store   │ │ Vector DB      │ │
│  │  (E11 : 8011)    │ │  (E3 : 8003)     │ │ (E6 : 8006)    │ │
│  ├──────────────────┤ ├──────────────────┤ ├────────────────┤ │
│  │ Gov Data Sync    │ │ Processed Meta   │ │ Chunks Engine  │ │
│  │  (E18 : 8018)    │ │  (E5 : 8005)     │ │ (E10 : 8010)   │ │
│  └──────────────────┘ └──────────────────┘ └────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                  LAYER 6: MONITORING & AUDIT                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Analytics Warehouse (E13 : 8013)              │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Categorization

| Category | Engines | Purpose |
|----------|---------|---------|
| **User Interaction** | Dashboard Interface (E14), Speech Interface (E20) | Frontend data aggregation, voice I/O |
| **Orchestration** | API Gateway (E0) | JWT validation, request routing, HTTP proxy to all engines |
| **Auth & Identity** | Login/Register (E1), Identity Engine (E2) | Registration, auth, PII vault, tokenized identity |
| **Deterministic Logic** | Eligibility Rules (E15), Simulation (E17), Deadline Monitoring (E16), Anomaly Detection (E8) | Boolean rule evaluation, what-if, scheduling, guardrails |
| **AI / LLM** | Neural Network (E7), Doc Understanding (E21) | NVIDIA NIM chat/RAG/intent, document parsing |
| **Data Normalization** | Metadata Engine (E4), JSON User Info (E12), Trust Scoring (E19) | Profile normalization, schema generation, trust signals |
| **Data Storage** | Raw Data Store (E3), Processed Metadata (E5), Vector DB (E6), Chunks Engine (E10), Policy Fetching (E11), Gov Data Sync (E18) | Immutable logs, user metadata, vector index, chunking, policy ingestion, government datasets |
| **Monitoring** | Analytics Warehouse (E13) | Aggregated metrics, funnel tracking |

---

## 2️⃣ Engine Dependency Graph

### Full Dependency Matrix

| Engine | Depends On (Data Source) | Calls (at Runtime) | Returns | Sync/Async | Reasoning |
|--------|--------------------------|---------------------|---------|------------|-----------|
| **API Gateway (E0)** | All 20 engines (HTTP proxy) | httpx to each engine | Proxied JSON response | Sync (request-response) | Single entry point; validates JWT, routes to engines |
| **Login/Register (E1)** | Shared DB (users table) | — | JWT tokens, user record | Sync | Standalone auth; no dependency on other engines |
| **Identity (E2)** | Shared DB (identity_records) | — | Encrypted PII vault, identity token | Sync | Standalone PII encryption; called after registration |
| **Raw Data Store (E3)** | Shared DB (raw_events) | — | Event ID, hash chain entry | Sync | Append-only immutable log; subscribes to event bus `*` within-process only |
| **Metadata (E4)** | Shared DB (metadata_records) | — | Normalized profile attributes | Sync | Pure data transformation; no upstream dependency |
| **Processed Metadata (E5)** | Shared DB (user_metadata, derived, cache, risk) | — | Stored user metadata + derived attributes | Sync | Reads whatever Metadata Engine normalized |
| **Vector DB (E6)** | Shared DB (vector_records) + in-memory HNSW index | — | Search results with similarity scores | Sync | Stateful; loads all vectors into memory on startup |
| **Neural Network (E7)** | NVIDIA NIM API (external) | NVIDIA NIM via `nvidia_client` | Chat response, RAG answer, intent, embeddings | Sync | External LLM call; ~1-5s latency per request |
| **Anomaly Detection (E8)** | Shared DB (anomaly_records) | — | Anomaly score (pass/review/block) | Sync | Stateless rule-based checks on input data |
| **Chunks Engine (E10)** | Shared DB (document_chunks) | — | Chunked document array | Sync | Pure text splitting; subscribes to `document.*` within-process only |
| **Policy Fetching (E11)** | Shared DB (fetched_documents, source_configs) + local filesystem | External HTTP (data.gov.in, PIB) | Fetched policy document | Sync | Crawls external sources; hash-based idempotency |
| **JSON User Info (E12)** | Shared DB (user_profiles) | — | Structured JSON profile | Sync | Aggregates from DB; no engine calls |
| **Analytics Warehouse (E13)** | Shared DB (analytics_events, metrics, funnels) | — | Aggregated metrics, dashboard data | Sync | Subscribes to `*` within-process only |
| **Dashboard Interface (E14)** | Shared DB (dashboard_preferences) | — | Widget descriptors, navigation JSON | Sync | BFF pattern; returns data_url for frontend to call gateway |
| **Eligibility Rules (E15)** | Shared DB (eligibility_rules, results) | — | Verdict: eligible/ineligible/partial/needs_verification | Sync | Pure deterministic boolean logic; zero LLM |
| **Deadline Monitoring (E16)** | Shared DB (scheme_deadlines, alerts) | — | Deadline list with urgency scores | Sync | Date/time calculations; no external calls |
| **Simulation (E17)** | Shared DB (simulation_results) + inline scheme rules | — | Schemes gained/lost, benefit delta | Sync | Has own copy of eligibility rules; no cross-engine call |
| **Gov Data Sync (E18)** | Shared DB (synced_datasets, records) + external data.gov.in API | External HTTP (data.gov.in) | Synced dataset records | Sync | Hash-based idempotency for re-sync |
| **Trust Scoring (E19)** | Shared DB (trust_scores) | — | Composite trust score 0.0-1.0 | Sync | Multi-signal scoring algorithm; no LLM |
| **Speech Interface (E20)** | NVIDIA NIM API (Riva ASR/TTS) | NVIDIA NIM via `nvidia_client` | Transcript, audio, language detection | Sync | External API for speech-to-text and text-to-speech |
| **Doc Understanding (E21)** | NVIDIA NIM API + Shared DB (processed_documents) | NVIDIA NIM via `nvidia_client` | Extracted fields, parsed document JSON | Sync | LLM-powered document parsing |

### Dependency Direction (Acyclic Verification)

```
No engine calls another engine via HTTP (except API Gateway).
No engine imports from another engine's codebase.
All engines import only from shared/ foundation.
Event bus is isolated per-process (no cross-process events).
Data flows through shared SQLite DB (one writer, many readers).

CIRCULAR DEPENDENCY CHECK: ✅ NONE DETECTED
```

The dependency graph is a **strict DAG** (Directed Acyclic Graph):
- Gateway → {all engines} (unidirectional proxy)
- All engines → shared/ (unidirectional import)
- All engines → shared DB (bidirectional R/W, but no engine depends on another engine's write for its own startup)

---

## 3️⃣ Final Request Flow (Runtime)

### Flow A: User Query (RAG Pipeline)

```
User (Browser/App)
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ API Gateway (E0:8000)                                    │
│  ├─ Validate JWT                                         │
│  ├─ Rate limit check                                     │
│  └─ Route: POST /api/v1/ai/chat                          │
└──────────┬───────────────────────────────────────────────┘
           │ httpx proxy
           ▼
┌──────────────────────────────────────────────────────────┐
│ Neural Network Engine (E7:8007)                          │
│  POST /ai/chat                                           │
│  ├─ Step 1: Classify intent (keyword + NIM fallback)     │
│  ├─ Step 2: Build system prompt with user context        │
│  ├─ Step 3: Call NVIDIA NIM (Llama 3.1 70B)              │
│  ├─ Step 4: Log conversation to DB (conversation_logs)   │
│  ├─ Step 5: Publish AI_RESPONSE_GENERATED event          │
│  └─ Return: { response, intent, confidence }             │
└──────────────────────────────────────────────────────────┘
```

**Current limitation:** The RAG flow does NOT automatically retrieve from Vector DB. The `/ai/rag` endpoint expects `context_passages` to be pre-provided by the caller. The orchestrator must chain: Vector Search → RAG Generation.

**Orchestrated RAG Flow (what must be built):**

```
Client → Gateway → [Orchestrator]
                        │
                        ├─ 1. POST /ai/intent (E7) → classify intent
                        │
                        ├─ 2. POST /vectors/search (E6) → retrieve Top-K chunks
                        │        query = user message
                        │        returns = context_passages[]
                        │
                        ├─ 3. POST /ai/rag (E7) → generate grounded answer
                        │        input = { query, context_passages, user_id }
                        │        returns = { response, sources }
                        │
                        ├─ 4. POST /anomaly/check (E8) → verify response quality
                        │        input = { user_id, data_points }
                        │        returns = { anomaly_score }
                        │
                        ├─ 5. POST /trust/score (E19) → compute trust score
                        │        input = { data sources, model confidence }
                        │        returns = { composite_score, level }
                        │
                        └─ 6. POST /raw-data/events (E3) → audit log
                                 input = { event_type: "AI_QUERY", payload }
```

**Caching points:**
- Vector search results: cached in E6 in-memory index (L1) + `LocalCache` (L2)
- RAG responses: cached in E7 `LocalCache` by query hash (TTL 1800s)
- Intent classification: cached in E7 by message hash

**Logging points:**
- Request enters gateway: `X-Request-ID` header generated (E0)
- AI response generated: `conversation_logs` table (E7)
- Event published: `AI_RESPONSE_GENERATED` event (in-process only)
- Audit log: `raw_events` table (E3) — must be explicitly called by orchestrator

---

### Flow B: Eligibility Check

```
Client → Gateway → POST /api/v1/eligibility/check
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ Eligibility Rules Engine (E15:8015)                      │
│  POST /eligibility/check                                 │
│  ├─ Input: user profile dict (age, income, state, etc.)  │
│  ├─ Step 1: Match against all BUILT_IN_RULES             │
│  │    └─ 8+ schemes: PM-KISAN, PMJAY, PMAY, etc.        │
│  ├─ Step 2: For each scheme, evaluate rules:             │
│  │    └─ field + operator + value → boolean              │
│  │    └─ Operators: eq, ne, lt, lte, gt, gte, in, etc.   │
│  ├─ Step 3: Compute verdict per scheme:                  │
│  │    └─ eligible / ineligible / partial / needs_verify   │
│  ├─ Step 4: Store results in eligibility_results table   │
│  ├─ Step 5: Publish ELIGIBILITY_COMPUTED event           │
│  └─ Return: { verdicts[], schemes_matched, confidence }  │
└──────────────────────────────────────────────────────────┘
```

**Critical invariant:** This flow is **100% deterministic**. No LLM is invoked. The eligibility verdict is a pure function of `(user_profile, scheme_rules) → verdict`. The LLM is only used downstream for explanation text (via E7).

**Orchestrated Eligibility with Explanation:**
```
[Orchestrator]
  ├─ 1. POST /eligibility/check (E15) → verdicts[]
  ├─ 2. POST /ai/summarize (E7) → human-readable explanation
  │        input = { text: JSON.stringify(verdicts) }
  │        returns = { summary }  (LLM generates "You qualify for PM-KISAN because...")
  └─ 3. POST /raw-data/events (E3) → audit log
```

---

### Flow C: What-If Simulation

```
Client → Gateway → POST /api/v1/simulate/what-if
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ Simulation Engine (E17:8017)                             │
│  POST /simulate/what-if                                  │
│  ├─ Input: { user_id, current_profile, changes }         │
│  ├─ Step 1: Clone current_profile                        │
│  ├─ Step 2: Apply changes to clone                       │
│  ├─ Step 3: Evaluate BOTH profiles against inline rules  │
│  │    └─ Uses own SCHEME_RULES (not E15's rules)         │
│  ├─ Step 4: Compute delta:                               │
│  │    └─ schemes_gained, schemes_lost, benefit_change    │
│  ├─ Step 5: Store in simulation_results table            │
│  ├─ Step 6: Publish SIMULATION_COMPLETED event           │
│  └─ Return: { before, after, delta, explanation }        │
└──────────────────────────────────────────────────────────┘
```

**Architecture note:** E17 has its **own inline copy** of scheme eligibility rules (8 schemes). This is intentional — it avoids a runtime dependency on E15 and allows simulation to run in complete isolation. The tradeoff is that rule updates must be synchronized manually between E15 and E17.

---

### Flow D: User Onboarding

```
Client → Gateway → POST /api/v1/auth/register
  │
  ├─ 1. POST /auth/register (E1)
  │        → Creates user record, returns JWT
  │        → Publishes USER_REGISTERED
  │
  ├─ 2. POST /identity/create (E2)
  │        → Encrypts PII (AES-256-GCM)
  │        → Returns identity_token
  │        → Publishes IDENTITY_CREATED
  │
  ├─ 3. POST /metadata/process (E4)
  │        → Normalizes profile fields
  │        → Derives age_group, income_bracket, state_normalized
  │        → Returns normalized profile
  │
  ├─ 4. POST /processed-metadata/store (E5)
  │        → Stores normalized metadata
  │        → Computes derived attributes
  │        → Publishes METADATA_STORED
  │
  ├─ 5. POST /eligibility/check (E15)
  │        → Batch evaluate all schemes
  │        → Cache results for dashboard
  │
  ├─ 6. POST /deadlines/check (E16)
  │        → Generate user-specific deadline alerts
  │
  └─ 7. POST /profile/generate/{user_id} (E12)
           → Build complete JSON profile
```

**Today:** Steps 2-7 must be triggered by the client (or orchestrator). They do not automatically chain from step 1. The event bus publishes `USER_REGISTERED` in E1's process, but no other engine receives it.

---

### Flow E: Voice Query

```
Client → Gateway → POST /api/v1/voice/transcribe
  │
  ├─ 1. POST /speech/transcribe (E20)
  │        → ASR via NVIDIA Riva
  │        → Returns { transcript, language }
  │
  ├─ 2. POST /ai/intent (E7)
  │        → Classify: scheme_query / eligibility / complaint / etc.
  │
  ├─ 3. [Route by intent]
  │     ├─ scheme_query → POST /ai/chat (E7)
  │     ├─ eligibility → POST /eligibility/check (E15)
  │     └─ complaint → POST /ai/chat (E7) with complaint prompt
  │
  ├─ 4. POST /speech/synthesize (E20)
  │        → TTS: convert response text to audio
  │
  └─ 5. POST /raw-data/events (E3) → audit
```

---

## 4️⃣ Background Flow (Ingestion & Scheduled Jobs)

### Pipeline 1: Policy Ingestion (Bootstrapping)

```
┌─────────────────────────────────────────────────────────────────┐
│                   POLICY INGESTION PIPELINE                     │
│                                                                 │
│  ① Policy Fetching Engine (E11)                                 │
│     │  - Crawls 10+ seeded sources                              │
│     │  - Fetches from data.gov.in, PIB, Gazette                 │
│     │  - IDEMPOTENCY: SHA-256 content_hash check                │
│     │    → If hash matches existing doc → SKIP                  │
│     │    → If new/changed → fetch, store, mark version          │
│     │  - Writes: fetched_documents table                        │
│     │  - Stores: raw text at data/policies/{scheme_id}.txt      │
│     │  - Publishes: POLICY_FETCHED event                        │
│     ▼                                                           │
│  ② Document Understanding Engine (E21)                          │
│     │  - LLM-powered extraction (NVIDIA NIM)                    │
│     │  - Extracts: eligibility criteria, benefit amounts,       │
│     │    application dates, required documents                  │
│     │  - Writes: processed_documents table                      │
│     │  - Publishes: DOCUMENT_PROCESSED event                    │
│     ▼                                                           │
│  ③ Chunks Engine (E10)                                          │
│     │  - Splits document into 512-token semantic chunks         │
│     │  - Maintains parent-child hierarchy                       │
│     │  - Writes: document_chunks table                          │
│     │  - Sets: embedding_status = "pending"                     │
│     │  - Publishes: CHUNKS_CREATED event (if EventType exists)  │
│     ▼                                                           │
│  ④ Neural Network Engine (E7)                                   │
│     │  - POST /ai/embeddings                                    │
│     │  - Uses NVIDIA NV-Embed-QA-E5-V5 model                   │
│     │  - Generates 1024-dim embeddings per chunk                │
│     │  - Returns: float[] per text                              │
│     ▼                                                           │
│  ⑤ Vector Database (E6)                                         │
│     │  - POST /vectors/upsert                                   │
│     │  - Stores embedding + metadata in vector_records table    │
│     │  - Rebuilds in-memory HNSW index                          │
│     │  - Deduplication: chunk_id uniqueness check               │
│     ▼                                                           │
│  ⑥ Raw Data Store (E3)                                          │
│     │  - POST /raw-data/events                                  │
│     │  - Logs entire pipeline execution as audit trail          │
│     │  - Immutable: SHA-256 hash chain                          │
│     ▼                                                           │
│  ⑦ Metadata Engine (E4)                                         │
│        - Tags: ministry, state, beneficiary type                │
│        - Writes: metadata_records table                         │
│                                                                 │
│  Re-ingestion idempotency:                                      │
│    E11 checks content_hash BEFORE downloading                   │
│    E6 checks chunk_id BEFORE inserting vectors                  │
│    E3 uses hash_chain for append-only integrity                 │
└─────────────────────────────────────────────────────────────────┘
```

**Critical note:** This pipeline does NOT execute automatically today. Each step must be triggered by an orchestrator or cron job. The event bus `document.*` subscription in E10 will only work if E21 and E10 run in the same process.

### Pipeline 2: Government Data Sync

```
┌─────────────────────────────────────────────────────────────────┐
│              GOVERNMENT DATA SYNC PIPELINE                      │
│                                                                 │
│  ① Gov Data Sync Engine (E18)                                   │
│     - POST /gov-data/sync/{dataset_id}                          │
│     - Fetches from data.gov.in API                              │
│     - IDEMPOTENCY: content_hash comparison                      │
│     - Datasets: NFHS-5, Census, SECC, SDG India Index           │
│     - Writes: synced_datasets, gov_data_records tables          │
│     - Stores: local JSON at data/gov-data/{dataset}.json        │
│     - Publishes: GOV_DATA_SYNCED event                          │
│                                                                 │
│  Trigger: HTTP POST (manual or cron)                            │
│  Frequency: Daily for active datasets, weekly for archival      │
│  Idempotency: Hash-based; skip if data unchanged               │
└─────────────────────────────────────────────────────────────────┘
```

### Pipeline 3: Deadline Monitoring Cron

```
┌─────────────────────────────────────────────────────────────────┐
│              DEADLINE MONITORING CRON FLOW                       │
│                                                                 │
│  ① Deadline Monitoring Engine (E16)                             │
│     - GET /deadlines/check?user_id={id}                         │
│     - Scans scheme_deadlines table                              │
│     - Computes days_remaining, urgency_score                    │
│     - Generates user_deadline_alerts records                    │
│     - Publishes: DEADLINE_ESCALATED if urgency_score > 0.8     │
│                                                                 │
│  Trigger: Cron job every 6 hours or on user dashboard load      │
│  Urgency scoring:                                               │
│    > 30 days  → 0.1 (low)                                       │
│    15-30 days → 0.3 (medium)                                    │
│    7-15 days  → 0.6 (high)                                      │
│    < 7 days   → 0.9 (critical)                                  │
│    Expired    → 1.0 (overdue)                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Pipeline 4: Analytics Aggregation

```
┌─────────────────────────────────────────────────────────────────┐
│              ANALYTICS AGGREGATION FLOW                          │
│                                                                 │
│  ① Analytics Warehouse (E13)                                    │
│     - POST /analytics/event                                     │
│     - Receives: event_type, user_id, properties                 │
│     - Writes: analytics_events table                            │
│                                                                 │
│  ② Metric Snapshots                                             │
│     - POST /analytics/snapshot                                  │
│     - Stores: metric_name, value, dimension, period             │
│                                                                 │
│  ③ Funnel Tracking                                              │
│     - POST /analytics/funnel                                    │
│     - Tracks: registration → eligibility → application funnels  │
│                                                                 │
│  Trigger: Each engine should POST analytics events after        │
│           completing significant operations. The orchestrator    │
│           must relay these calls.                                │
│                                                                 │
│  Today's limitation: E13 subscribes to `*` on event bus, but    │
│  only receives events from its own process. The orchestrator    │
│  must explicitly POST audit events to E13 after each pipeline   │
│  step.                                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5️⃣ Orchestrator Design

### Architecture Decision: **Hybrid Controller + Tool-Calling Agent**

The orchestrator is NOT a single new engine. It is a **routing and chaining layer inside the API Gateway** (E0) that:

1. **Controller mode** (deterministic flows): Hardcoded pipeline steps for well-defined flows (onboarding, eligibility check, ingestion). These are predictable, always execute the same sequence, and must not involve LLM decision-making.

2. **Tool-calling agent mode** (open-ended queries): For user questions that require intent classification → dynamic routing → multi-engine aggregation. The Neural Network Engine (E7) acts as the "brain" that decides which tools to invoke.

### Why NOT pure event-driven?

The in-process event bus means engine-to-engine event propagation is currently **non-functional across processes**. Building a cross-process event bus (Redis Streams, NATS, Kafka) is a future scaling task. For MVP, the orchestrator must use **sequential HTTP chaining** — reliable, debuggable, and compatible with the hub-and-spoke topology.

### Why NOT a separate orchestrator engine?

Adding Engine 22 creates another deployment unit and another network hop. Since the Gateway already has `httpx` and `proxy_request()` infrastructure, the orchestration logic belongs there as **composite routes** — routes that call multiple engines in sequence.

### Orchestrator Design Specification

```python
# Conceptual structure (lives in api-gateway/)

# ── Composite Route: Full RAG Query ──────────────────────────
# POST /api/v1/query
# This is NOT a simple proxy — it chains 4 engines.

async def orchestrated_query(request):
    user_msg = request.body["message"]
    user_id = request.user["user_id"]

    # Step 1: Intent classification (E7)
    intent = await call_engine(E7, "/ai/intent", {"message": user_msg})

    # Step 2: Vector search (E6)
    chunks = await call_engine(E6, "/vectors/search",
                               {"query": user_msg, "top_k": 5})

    # Step 3: RAG generation (E7)
    answer = await call_engine(E7, "/ai/rag", {
        "query": user_msg,
        "context_passages": chunks["results"],
        "user_id": user_id,
    })

    # Step 4: Anomaly check (E8)
    anomaly = await call_engine(E8, "/anomaly/check", {
        "user_id": user_id,
        "data_points": {"response_length": len(answer["response"])},
    })

    # Step 5: Audit log (E3)
    await call_engine(E3, "/raw-data/events", {
        "event_type": "AI_QUERY",
        "source_engine": "orchestrator",
        "user_id": user_id,
        "payload": {"query": user_msg, "intent": intent, "anomaly": anomaly},
    })

    return {answer, trust_score, anomaly_check}
```

### Orchestrator Principles

| Principle | Implementation |
|-----------|---------------|
| **No direct engine-to-engine coupling** | All cross-engine calls go through the orchestrator (in the gateway) |
| **Error isolation** | Each `call_engine()` has independent try/catch; partial failures return degraded responses |
| **Retry safety** | Only idempotent operations (GET, hash-checked POST) are retried. Non-idempotent writes (user creation) are NOT retried |
| **Timeout cascading** | Gateway timeout (30s) > Individual engine timeout (10s) > LLM timeout (15s). Inner timeouts fire before outer timeout |
| **Request correlation** | Single `X-Request-ID` propagated through all chained calls for end-to-end tracing |
| **Audit trail** | Every composite flow ends with a POST to Raw Data Store (E3) |

### Composite Routes to Implement

| Route | Type | Pipeline |
|-------|------|----------|
| `POST /api/v1/query` | Agent | Intent → Vector Search → RAG → Anomaly → Audit |
| `POST /api/v1/onboard` | Controller | Register → Identity → Metadata → Store → Eligibility → Deadlines → Profile |
| `POST /api/v1/check-eligibility` | Controller | Eligibility Check → (optional) AI Explanation → Audit |
| `POST /api/v1/ingest-policy` | Controller | Fetch → Document Parse → Chunk → Embed → Vector Upsert → Audit |
| `POST /api/v1/voice-query` | Agent | Transcribe → Intent → Route by intent → Synthesize → Audit |
| `POST /api/v1/simulate` | Controller | Simulation → (optional) AI Explanation → Audit |

---

## 6️⃣ LLM Boundary Definition

### What the LLM IS Allowed to Do

| Capability | Engine | Endpoint | Model |
|------------|--------|----------|-------|
| **Conversational Q&A** | Neural Network (E7) | `/ai/chat` | Llama 3.1 70B |
| **RAG-grounded answers** | Neural Network (E7) | `/ai/rag` | Llama 3.1 70B |
| **Intent classification** | Neural Network (E7) | `/ai/intent` | Keyword + Llama 3.1 8B fallback |
| **Text summarization** | Neural Network (E7) | `/ai/summarize` | Llama 3.1 70B |
| **Language translation** | Neural Network (E7) | `/ai/translate` | Llama 3.1 70B |
| **Text embeddings** | Neural Network (E7) | `/ai/embeddings` | NV-Embed-QA-E5-V5 |
| **Document extraction** | Doc Understanding (E21) | `/documents/parse` | Llama 3.1 70B |
| **Speech-to-text** | Speech Interface (E20) | `/speech/transcribe` | NVIDIA Riva ASR |
| **Text-to-speech** | Speech Interface (E20) | `/speech/synthesize` | NVIDIA Riva TTS |
| **Natural language explanation** | Neural Network (E7) | `/ai/summarize` | Llama 3.1 8B |

### What the LLM is NOT Allowed to Do

| Prohibited Action | Why | Enforced By |
|-------------------|-----|-------------|
| **Determine eligibility verdicts** | Must be deterministic boolean logic | E15 uses pure Python boolean operators; no NIM call |
| **Compute trust scores** | Must be algorithmic and auditable | E19 uses weighted formula; no LLM |
| **Compute anomaly scores** | Must be deterministic threshold checks | E8 uses statistical rules; no LLM |
| **Modify user data** | LLM must never write to identity/metadata stores | E2, E4, E5 have no NIM dependency |
| **Make scheduling decisions** | Deadlines are date arithmetic | E16 uses Python `datetime`; no LLM |
| **Generate simulation results** | What-if is profile diff + rule re-evaluation | E17 uses inline rules; no LLM |
| **Decide routing/orchestration** | Pipeline steps are hardcoded | Orchestrator uses deterministic if/else |

### Structured Input/Output Contract

**Input to LLM** (always structured):
```json
{
  "system_prompt": "You are an Indian government schemes expert...",
  "user_message": "Am I eligible for PM-KISAN?",
  "context_passages": ["chunk1...", "chunk2..."],  // from Vector DB
  "user_profile": { "state": "UP", "occupation": "farmer" },  // from Metadata
  "temperature": 0.3,  // low for factual accuracy
  "max_tokens": 1024
}
```

**Output validation:**
- E7 wraps all LLM responses in `ApiResponse` (Pydantic validated)
- Response always includes `confidence` score (from NIM)
- Response always includes `model` identifier
- If LLM returns malformed JSON or refuses to answer, E7 returns a safe fallback
- E8 (Anomaly Detection) can flag responses with anomaly_score = "block" if suspicious

### LLM Guardrails

```
1. System prompt injection defense: All user input is placed in the
   user message slot, never in the system prompt.
2. Context grounding: RAG responses are grounded in retrieved chunks;
   the prompt instructs "only answer based on provided context."
3. Hallucination check: E8 can verify that cited scheme names exist
   in the eligibility_rules table.
4. Token limit: max_tokens=1024 prevents runaway generation.
5. Temperature: 0.3 for factual queries, 0.7 for conversational.
```

---

## 7️⃣ Failure Handling Strategy

### Failure Matrix

| Component | Failure Mode | Impact | Mitigation | Recovery |
|-----------|-------------|--------|------------|----------|
| **Vector DB (E6)** | Process crash / OOM | RAG search fails → no context passages | Return degraded response: "I can answer from general knowledge but cannot cite specific policies right now." | E6 rebuilds in-memory index from DB on restart (SELECT all from `vector_records` at startup) |
| **LLM / NVIDIA NIM** | API timeout (>15s) / 429 rate limit / 5xx | Chat, RAG, summarize, translate fail | Three API keys configured (rotate on 429). Timeout at 15s. Return: "AI service temporarily unavailable. Your eligibility results are still valid (computed deterministically)." | Retry with exponential backoff (2s, 4s, 8s). Max 3 retries. Switch to `NIM_MODEL_8B` if 70B is down. |
| **Eligibility Rules (E15)** | Process crash / DB lock | Cannot compute verdicts | Return cached results if available (LocalCache TTL=1800s). If no cache: "Unable to compute eligibility right now. Please try again." | Restart E15. Results are idempotent — re-running produces same output. |
| **Policy Ingestion (E11)** | External source unreachable / partial download | New policies not ingested | IDEMPOTENT: Content hash prevents partial re-ingestion. Failed fetches logged with `sync_status = "error"`. Existing policies remain valid. | Retry fetch on next cron cycle. No data corruption possible due to hash-before-write. |
| **Raw Data Store (E3)** | DB full / write failure | Audit trail gap | Log to local filesystem fallback (`data/raw-store/hot/`). E3 already writes JSON files in addition to DB. | Reconcile filesystem logs with DB on recovery. Hash chain can be rebuilt. |
| **SQLite DB** | Write contention / file lock timeout | Any write-heavy engine blocks | WAL mode is enabled (concurrent readers, single writer). Write timeout set. | Under heavy load, queue writes. Future: migrate to PostgreSQL (connection string in config already parameterized). |
| **Speech Engine (E20)** | Riva API down / audio codec failure | Voice input/output fails | Graceful degradation to text-only mode. Dashboard interface works without voice. | Retry ASR/TTS with fallback to simpler codec. |
| **Dashboard (E14)** | Cache miss / DB timeout | Widget data stale | Widgets include `data_url` — frontend can fetch directly from gateway if BFF is slow. | Clear cache, restart. Stateless engine recovers instantly. |

### Error Propagation Rules

```
1. Engine-level errors → 500 with structured error body
2. Gateway proxy errors → 503 (engine down) or 504 (timeout)
3. Validation errors → 422 with field-level details
4. Auth errors → 401 (missing JWT) or 403 (insufficient role)
5. Orchestrator partial failure → Return available data with
   degradation flags: { "data": {...}, "degraded": ["vector_search"] }
```

### Circuit Breaker Pattern (in Gateway)

```
For each downstream engine:
  - Track: last N request outcomes (success/fail)
  - CLOSED (normal): Forward all requests
  - OPEN (tripped): Reject immediately with 503 after 5 consecutive failures
  - HALF-OPEN (probe): After 30s, allow 1 request through to test recovery
  - Reset on success

Implementation: Per-engine failure counter in gateway memory.
No shared state needed (single gateway instance for MVP).
```

---

## 8️⃣ Scalability Alignment

### Current State (MVP — Single Machine)

```
┌─────────────────────────────────────────────┐
│         Single Machine (Local Dev)          │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ 21 × uvicorn processes             │    │
│  │ 1 × SQLite database (WAL mode)     │    │
│  │ 1 × Local filesystem (data/)       │    │
│  │ 1 × In-memory event bus (per proc) │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  Bottleneck: SQLite single-writer lock      │
│  Bottleneck: No cross-process events        │
│  Bottleneck: In-memory vector index (RAM)   │
└─────────────────────────────────────────────┘
```

### Scale Path 1: Vertical (Same Machine, More Power)

| Change | Impact | Effort |
|--------|--------|--------|
| Replace SQLite with PostgreSQL | Concurrent writes, connection pooling | Low — change `DATABASE_URL` in config.py |
| Add Redis for caching | Cross-process cache, pub/sub events | Low — `USE_REDIS=True` already in config |
| Increase uvicorn workers per engine | Handle more concurrent requests per engine | Trivial — `--workers N` flag |

### Scale Path 2: Horizontal (Multiple Machines)

| Change | Impact | Effort |
|--------|--------|--------|
| Replace LocalEventBus with Redis Streams/NATS | Cross-process, cross-machine events | Medium — swap `event_bus.py` implementation |
| Replace local filesystem with S3/MinIO | Shared storage across instances | Medium — swap file ops in E3, E11, E18, E20 |
| Containerize each engine (Docker) | Independent scaling per engine | Medium — 1 Dockerfile per engine |
| Kubernetes deployment | Auto-scaling, health probes, rolling updates | High — K8s manifests, service mesh |
| Replace in-memory vector index with Milvus/Qdrant | Distributed vector search, persistence | Medium — swap E6 internals |

### Design Properties That Enable Scaling

| Property | Current Implementation | Why It Scales |
|----------|----------------------|---------------|
| **No shared mutable state between engines** | Each engine owns its DB tables; no cross-engine transactions | Engines can be deployed independently |
| **Stateless request handling** | All engines are stateless (state in DB/cache) | Any instance can handle any request |
| **Idempotent ingestion** | Hash-based dedup in E11, E18, E6 | Safe to run multiple ingestors concurrently |
| **Config-driven URLs** | `ENGINE_URLS` dict in config.py | Swap localhost → K8s service DNS names |
| **Token-based auth** | JWT with HS256 (stateless validation) | No session stickiness required |
| **Event bus interface** | `publish()` / `subscribe()` API | Swap implementation without changing callers |
| **Database URL parameterized** | `DATABASE_URL` in config.py | Swap SQLite → PostgreSQL without code changes |

### Anti-Patterns Avoided

```
✅ No engine imports from another engine's codebase
✅ No hardcoded localhost URLs in engine code (all via config)
✅ No global mutable singletons shared across engines (event bus is per-process)
✅ No file-based locking between engines
✅ No engine-to-engine direct HTTP calls (only gateway proxies)
✅ No shared in-memory cache across processes
```

### Future Event Bus Integration Plan

```
Phase 1 (Current): In-memory LocalEventBus (per-process)
  → Events are fire-and-forget within each engine process
  → Cross-engine events do NOT propagate

Phase 2 (Redis Pub/Sub): Replace LocalEventBus with Redis
  → shared/event_bus.py swaps to redis.asyncio
  → Same publish()/subscribe() interface
  → Cross-engine events now propagate
  → Analytics Warehouse (E13) receives all events from all engines
  → Chunks Engine (E10) receives DOCUMENT_PROCESSED from E21

Phase 3 (Kafka/NATS): Replace Redis with durable message broker
  → Guaranteed delivery, replay capability
  → Consumer groups for load balancing
  → Dead letter queue becomes persistent

Migration path: Only shared/event_bus.py changes.
No engine code needs modification.
```

---

## 9️⃣ Clean Final Architecture Diagram

### Complete System Flow (Text-Based)

```
╔══════════════════════════════════════════════════════════════════════╗
║                        USER INTERFACES                              ║
║                                                                      ║
║   Browser/App ◄──────────────────────────► Mobile Voice              ║
║       │                                         │                    ║
╚═══════╪═════════════════════════════════════════╪════════════════════╝
        │ HTTPS                                   │ HTTPS
        ▼                                         ▼
╔══════════════════════════════════════════════════════════════════════╗
║                     API GATEWAY (E0 : 8000)                         ║
║                                                                      ║
║  ┌────────────┐  ┌──────────────┐  ┌──────────────────────────┐     ║
║  │ JWT Auth   │  │ Rate Limiter │  │ Request ID + CORS        │     ║
║  └─────┬──────┘  └──────┬───────┘  └──────────┬───────────────┘     ║
║        │                │                      │                     ║
║  ┌─────▼────────────────▼──────────────────────▼───────────────┐    ║
║  │                  ORCHESTRATOR LAYER                          │    ║
║  │                                                              │    ║
║  │  ┌──────────────────────────────────────────────────────┐   │    ║
║  │  │ COMPOSITE ROUTES (chained multi-engine calls)        │   │    ║
║  │  │  /api/v1/query         → Intent→VectorDB→RAG→Audit  │   │    ║
║  │  │  /api/v1/onboard       → Register→Identity→Meta→... │   │    ║
║  │  │  /api/v1/ingest-policy → Fetch→Parse→Chunk→Embed    │   │    ║
║  │  │  /api/v1/voice-query   → ASR→Intent→Route→TTS       │   │    ║
║  │  └──────────────────────────────────────────────────────┘   │    ║
║  │                                                              │    ║
║  │  ┌──────────────────────────────────────────────────────┐   │    ║
║  │  │ SIMPLE PROXIES (direct pass-through)                 │   │    ║
║  │  │  /api/v1/auth/*       → E1 (Login/Register)          │   │    ║
║  │  │  /api/v1/identity/*   → E2 (Identity)                │   │    ║
║  │  │  /api/v1/eligibility/*→ E15 (Eligibility Rules)      │   │    ║
║  │  │  /api/v1/simulate/*   → E17 (Simulation)             │   │    ║
║  │  │  /api/v1/deadlines/*  → E16 (Deadline Monitor)       │   │    ║
║  │  │  /api/v1/schemes/*    → E11 (Policy Fetching)        │   │    ║
║  │  │  /api/v1/dashboard/*  → E14 (Dashboard BFF)          │   │    ║
║  │  │  /api/v1/analytics/*  → E13 (Analytics)              │   │    ║
║  │  │  /api/v1/trust/*      → E19 (Trust Scoring)          │   │    ║
║  │  │  /api/v1/profile/*    → E12 (JSON User Info)         │   │    ║
║  │  │  /api/v1/documents/*  → E21 (Doc Understanding)      │   │    ║
║  │  │  /api/v1/voice/*      → E20 (Speech Interface)       │   │    ║
║  │  └──────────────────────────────────────────────────────┘   │    ║
║  └──────────────────────────────────────────────────────────────┘    ║
╚══════════╪═══════════════════════════════════════════════════════════╝
           │ httpx (async)
           ▼
╔══════════════════════════════════════════════════════════════════════╗
║                     ENGINE FLEET (20 Engines)                       ║
║                                                                      ║
║  ┌─────────── AUTH & IDENTITY ───────────────────────────────────┐  ║
║  │  E1:8001 Login/Register    E2:8002 Identity Engine            │  ║
║  └───────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
║  ┌─────────── INTELLIGENCE (LLM-Powered) ───────────────────────┐  ║
║  │  E7:8007  Neural Network ←──── NVIDIA NIM API (external)     │  ║
║  │  E21:8021 Doc Understanding ←── NVIDIA NIM API (external)    │  ║
║  │  E20:8020 Speech Interface ←── NVIDIA Riva API (external)    │  ║
║  └───────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
║  ┌─────────── DATA NORMALIZATION ────────────────────────────────┐  ║
║  │  E4:8004  Metadata Engine                                     │  ║
║  │  E12:8012 JSON User Info Generator                            │  ║
║  │  E19:8019 Trust Scoring Engine                                │  ║
║  └───────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
║  ┌─────────── DETERMINISTIC LOGIC ───────────────────────────────┐  ║
║  │  E15:8015 Eligibility Rules (BOOLEAN only, NO LLM)            │  ║
║  │  E17:8017 Simulation Engine (inline rules, NO LLM)            │  ║
║  │  E16:8016 Deadline Monitoring (date arithmetic, NO LLM)       │  ║
║  │  E8:8008  Anomaly Detection (statistical rules, NO LLM)      │  ║
║  └───────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
║  ┌─────────── DATA LAYER ────────────────────────────────────────┐  ║
║  │  E3:8003  Raw Data Store (immutable, hash-chained)            │  ║
║  │  E5:8005  Processed User Metadata Store                       │  ║
║  │  E6:8006  Vector Database (in-memory HNSW + SQLite)           │  ║
║  │  E10:8010 Chunks Engine (semantic splitting)                  │  ║
║  │  E11:8011 Policy Fetching (crawl + hash dedup)                │  ║
║  │  E18:8018 Gov Data Sync (data.gov.in + hash dedup)            │  ║
║  └───────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
║  ┌─────────── USER INTERACTION ──────────────────────────────────┐  ║
║  │  E14:8014 Dashboard Interface (BFF — widget descriptors)      │  ║
║  └───────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
║  ┌─────────── MONITORING ────────────────────────────────────────┐  ║
║  │  E13:8013 Analytics Warehouse (metrics, funnels)              │  ║
║  └───────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
           │
           ▼
╔══════════════════════════════════════════════════════════════════════╗
║                     SHARED FOUNDATION                               ║
║                                                                      ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ shared/config.py      — Ports, API keys, URLs, data paths     │ ║
║  │ shared/database.py    — SQLAlchemy async engine, Base, init_db│ ║
║  │ shared/models.py      — Pydantic models, EventType enum       │ ║
║  │ shared/event_bus.py   — LocalEventBus (in-memory per-process) │ ║
║  │ shared/cache.py       — L1 memory + L2 file cache             │ ║
║  │ shared/nvidia_client.py — OpenAI SDK wrapper for NIM          │ ║
║  │ shared/utils.py       — JWT, hashing, ID generation           │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  ┌────────────────────────────────────────────────────────────────┐ ║
║  │ data/aiforbharat.db   — Shared SQLite (WAL mode)              │ ║
║  │ data/cache/           — L2 file cache (per-namespace dirs)    │ ║
║  │ data/raw-store/       — Hot/Warm/Cold event files             │ ║
║  │ data/policies/        — Fetched policy text files             │ ║
║  │ data/gov-data/        — Synced government dataset JSON files  │ ║
║  │ data/audio/           — Voice session recordings              │ ║
║  └────────────────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════════╝
```

### Data Flow Diagram (Simplified)

```
                    ┌──────────────────┐
                    │    USER INPUT    │
                    │ text / voice /   │
                    │ profile update   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   API GATEWAY    │
                    │    (E0:8000)     │
                    │  JWT + Route +   │
                    │  Orchestrate     │
                    └────────┬─────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼──────┐ ┌──────▼───────┐ ┌──────▼───────┐
    │  AUTH PATH   │ │  QUERY PATH  │ │ INGEST PATH  │
    │              │ │              │ │              │
    │ E1→E2→E4→E5 │ │ E7→E6→E7→E8 │ │ E11→E21→E10 │
    │   →E15→E12  │ │   →E19→E3   │ │  →E7→E6→E3  │
    └──────────────┘ └──────────────┘ └──────────────┘
            │                │                │
            ▼                ▼                ▼
    ┌──────────────────────────────────────────────┐
    │            SHARED SQLITE DATABASE            │
    │              data/aiforbharat.db             │
    └──────────────────────────────────────────────┘
            │
            ▼
    ┌──────────────────────────────────────────────┐
    │         ANALYTICS WAREHOUSE (E13)            │
    │     (receives audit events from gateway)     │
    └──────────────────────────────────────────────┘
```

---

## Appendix A: Known Integration Issues (Pre-Fix)

These issues were identified during this analysis and must be addressed before the orchestrator is implemented:

### Issue 1: Dashboard Engine Port Attribute Names

`dashboard-interface/main.py` line ~253 references attribute names like `settings.LOGIN_REGISTER_ENGINE_PORT`, `settings.PROCESSED_METADATA_STORE_PORT`, `settings.NEURAL_NETWORK_ENGINE_PORT`, etc. These do NOT exist in `shared/config.py` which uses names like `settings.LOGIN_REGISTER_PORT`, `settings.PROCESSED_METADATA_PORT`, `settings.NEURAL_NETWORK_PORT`, etc. The `/dashboard/engines/status` endpoint will crash with `AttributeError` at runtime.

**Status:** Must fix before orchestrator integration. The endpoint is non-critical (status page only) but will cause 500 errors.

### Issue 2: Missing EventType Enum Values

Several engines publish events using event type strings that may not exist in the `EventType` enum. If an engine uses `EventType.CHUNKS_CREATED` or `EventType.AI_QUERY_PROCESSED` but these aren't in the enum, the `EventMessage` Pydantic model will reject them with a validation error.

**Status:** Must audit all `event_bus.publish()` calls and ensure every event type referenced exists in `shared/models.py`.

### Issue 3: In-Process Event Bus Limitation

The `LocalEventBus` is a per-process singleton. The three subscribing engines (E3 on `*`, E10 on `document.*`, E13 on `*`) only receive events from their own process.

**Impact:**  
- E10 (Chunks) will NEVER auto-chunk when E21 (Doc Understanding) publishes `DOCUMENT_PROCESSED`
- E13 (Analytics) will NEVER receive events from any other engine
- E3 (Raw Data) will NEVER auto-log events from other engines

**Mitigation:** The orchestrator must explicitly POST to E3 and E13 after each pipeline step. The E11→E21→E10 pipeline must be chained via HTTP, not events.

### Issue 4: Simulation Engine Rule Duplication

E17 (Simulation) has its own `SCHEME_RULES` dict (8 schemes) duplicated from E15 (Eligibility). If E15's rules are updated (new schemes added, criteria changed), E17's inline copy becomes stale.

**Mitigation options:**
1. E17 calls E15 via HTTP for rule evaluation (adds coupling)
2. Both E15 and E17 read rules from the shared DB `eligibility_rules` table
3. Accept the duplication for MVP and synchronize manually

**Recommendation:** Option 2 — both engines read from the same `eligibility_rules` DB table. E15 already seeds this table on startup.

### Issue 5: Missing Gateway Routes for Internal Engines

Five engines have no proxy routes in the API Gateway:
- Raw Data Store (E3) — no `/api/v1/raw-data/*` route
- Processed Metadata (E5) — no `/api/v1/processed-metadata/*` route  
- Vector Database (E6) — no `/api/v1/vectors/*` route
- Anomaly Detection (E8) — no `/api/v1/anomaly/*` route
- Chunks Engine (E10) — no `/api/v1/chunks/*` route

**Impact:** These engines cannot be reached through the gateway. The orchestrator's composite routes must call them directly via `httpx` (which the gateway already has).

**Recommendation:** Add proxy routes for all 5
 engines, even if they're marked as "internal" — the orchestrator needs them, and admin tooling will benefit.

---

## Appendix B: Execution Order Guarantee

For any composite flow, the orchestrator must enforce this execution order:

### Strict Ordering (Sequential — Each Step Depends on Previous)

```
ONBOARDING:   E1 → E2 → E4 → E5 → E15 → E16 → E12 → E3
              │    │    │    │     │      │      │     └─ audit
              │    │    │    │     │      │      └─ profile gen
              │    │    │    │     │      └─ deadline check
              │    │    │    │     └─ eligibility batch
              │    │    │    └─ store processed metadata
              │    │    └─ normalize profile
              │    └─ encrypt PII
              └─ create user + JWT

RAG QUERY:    E7(intent) → E6(search) → E7(rag) → E8(anomaly) → E19(trust) → E3(audit)
              │             │             │          │              │            └─ log
              │             │             │          │              └─ score
              │             │             │          └─ check
              │             │             └─ generate with context
              │             └─ retrieve chunks
              └─ classify intent

INGESTION:    E11(fetch) → E21(parse) → E10(chunk) → E7(embed) → E6(upsert) → E4(tag) → E3(audit)
```

### Parallelizable Steps (Can Run Concurrently)

```
After eligibility check (E15):
  ├─ E7(explain) — AI explanation     ┐
  └─ E16(deadlines) — deadline check  ┘  can run in parallel

After onboarding metadata stored (E5):
  ├─ E15(eligibility) — batch check   ┐
  └─ E19(trust) — initial score       ┘  can run in parallel

After RAG generation (E7):
  ├─ E8(anomaly) — check response     ┐
  └─ E19(trust) — score response      ┘  can run in parallel
```

---

## Appendix C: Configuration Reference

### Engine Port Map (from shared/config.py)

| Engine | Config Field | Port |
|--------|-------------|------|
| API Gateway | `API_GATEWAY_PORT` | 8000 |
| Login/Register | `LOGIN_REGISTER_PORT` | 8001 |
| Identity | `IDENTITY_ENGINE_PORT` | 8002 |
| Raw Data Store | `RAW_DATA_STORE_PORT` | 8003 |
| Metadata | `METADATA_ENGINE_PORT` | 8004 |
| Processed Metadata | `PROCESSED_METADATA_PORT` | 8005 |
| Vector Database | `VECTOR_DATABASE_PORT` | 8006 |
| Neural Network | `NEURAL_NETWORK_PORT` | 8007 |
| Anomaly Detection | `ANOMALY_DETECTION_PORT` | 8008 |
| *(unused)* | — | 8009 |
| Chunks Engine | `CHUNKS_ENGINE_PORT` | 8010 |
| Policy Fetching | `POLICY_FETCHING_PORT` | 8011 |
| JSON User Info | `JSON_USER_INFO_PORT` | 8012 |
| Analytics Warehouse | `ANALYTICS_WAREHOUSE_PORT` | 8013 |
| Dashboard BFF | `DASHBOARD_BFF_PORT` | 8014 |
| Eligibility Rules | `ELIGIBILITY_RULES_PORT` | 8015 |
| Deadline Monitoring | `DEADLINE_MONITORING_PORT` | 8016 |
| Simulation | `SIMULATION_ENGINE_PORT` | 8017 |
| Gov Data Sync | `GOV_DATA_SYNC_PORT` | 8018 |
| Trust Scoring | `TRUST_SCORING_PORT` | 8019 |
| Speech Interface | `SPEECH_INTERFACE_PORT` | 8020 |
| Doc Understanding | `DOC_UNDERSTANDING_PORT` | 8021 |

### ENGINE_URLS Keys (for httpx calls in orchestrator)

```python
ENGINE_URLS = {
    "api_gateway":        "http://localhost:8000",
    "login_register":     "http://localhost:8001",
    "identity":           "http://localhost:8002",
    "raw_data_store":     "http://localhost:8003",
    "metadata":           "http://localhost:8004",
    "processed_metadata": "http://localhost:8005",
    "vector_database":    "http://localhost:8006",
    "neural_network":     "http://localhost:8007",
    "anomaly_detection":  "http://localhost:8008",
    "chunks":             "http://localhost:8010",
    "policy_fetching":    "http://localhost:8011",
    "json_user_info":     "http://localhost:8012",
    "analytics_warehouse":"http://localhost:8013",
    "dashboard_bff":      "http://localhost:8014",
    "eligibility_rules":  "http://localhost:8015",
    "deadline_monitoring":"http://localhost:8016",
    "simulation":         "http://localhost:8017",
    "gov_data_sync":      "http://localhost:8018",
    "trust_scoring":      "http://localhost:8019",
    "speech_interface":   "http://localhost:8020",
    "doc_understanding":  "http://localhost:8021",
}
```

---

*Document generated: February 28, 2026*  
*Architecture version: 1.0*  
*Next action: Implement composite routes in API Gateway based on Section 5*
