# AIforBharat — Orchestrator Implementation Blueprint

> **Date:** February 28, 2026
> **Author:** Senior Distributed Systems Architect
> **Status:** Verified — Integration Testing Passed
> **Scope:** Orchestrator layer inside API Gateway. No engine redesign. No new architectural layers.

---

## 1️⃣ Orchestrator Final Architecture

> **Update (Feb 28):** The Orchestrator composite routes have been fully validated using `test_orchestration.py`. Full reports are available in `orchestra-testing-1.md`. Additionally, the orchestrator integration points, request schemas, and inter-engine dependencies are now fully documented across the `API Gateway README` and all 21 downstream engine READMEs.

### Design Decision: Orchestrator Inside the API Gateway

The orchestrator is **not** a separate engine. It is a Python module (`api-gateway/orchestrator.py`) registered as an additional FastAPI router in the API Gateway process. This decision is driven by three facts:

1. **Hub-and-Spoke Topology** — Only the API Gateway makes cross-engine HTTP calls. Adding orchestration logic here reuses the existing `httpx` infrastructure and avoids a 22nd process.
2. **Zero New Network Hops** — The orchestrator runs in-process with the gateway. Composite routes call downstream engines with the same `httpx.AsyncClient` that proxy routes use.
3. **Single Deployment Unit** — No additional port, no additional `uvicorn` process, no additional health check endpoint to monitor.

### Architectural Layers (Post-Implementation)

```
┌────────────────────────────────────────────────────────────────┐
│                    API GATEWAY (E0 : 8000)                     │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  MIDDLEWARE: JWT Auth → Rate Limiter → Request ID       │   │
│  └──────────┬──────────────────────────────────────────────┘   │
│             │                                                  │
│  ┌──────────▼──────────────────────────────────────────────┐   │
│  │  ORCHESTRATOR ROUTER (api-gateway/orchestrator.py)      │   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ CIRCUIT BREAKER (per-engine failure tracking)      │  │   │
│  │  │ call_engine() with timeout + retry safety          │  │   │
│  │  │ audit_log() fire-and-forget to E3 + E13            │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │                                                          │   │
│  │  COMPOSITE ROUTES:                                       │   │
│  │    POST /api/v1/query           — RAG pipeline           │   │
│  │    POST /api/v1/onboard         — User onboarding        │   │
│  │    POST /api/v1/check-eligibility — Eligibility + explain│   │
│  │    POST /api/v1/ingest-policy   — Policy ingestion       │   │
│  │    POST /api/v1/voice-query     — Voice pipeline         │   │
│  │    POST /api/v1/simulate        — What-if + explain      │   │
│  │    GET  /api/v1/circuit-breaker/status — CB status       │   │
│  │    GET  /api/v1/engines/health  — Fleet health probe     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PROXY ROUTER (api-gateway/routes.py)                    │   │
│  │                                                          │   │
│  │  21 direct pass-through routes to individual engines     │   │
│  │  (including 6 newly added: raw-data, processed-metadata, │   │
│  │   vectors, anomaly, chunks, gov-data)                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

### Route Precedence

The `orchestrator_router` is mounted **before** `gateway_router` in `main.py`. FastAPI matches routes in registration order. This means:

- `POST /api/v1/simulate` → **Orchestrator** (composite route with E17 + E7 + audit)
- `GET /api/v1/simulate/results` → **Proxy** (direct pass-through to E17, since orchestrator only handles POST)

This is intentional: composite routes intercept specific operations, while proxy routes provide full API access to individual engines.

---

## 2️⃣ Concrete Execution Graphs

### Graph A: RAG Query (`POST /api/v1/query`)

```
                    ┌─────────────┐
                    │  Client     │
                    └──────┬──────┘
                           │ POST /api/v1/query
                           │ {message, user_id, top_k}
                    ┌──────▼──────┐
                    │  Middleware  │
                    │  JWT + Rate │
                    └──────┬──────┘
                           │
         ┌─────────────────▼─────────────────┐
         │         ORCHESTRATOR              │
         │                                    │
         │  ① E7 /ai/intent ─────────────────│─── classify intent
         │       │                            │
         │  ② E6 /vectors/search ────────────│─── retrieve top-K chunks
         │       │                            │
         │  ③ E7 /ai/rag (or /ai/chat) ─────│─── grounded generation
         │       │                            │
         │  ④┬─ E8 /anomaly/check  ──────────│─┐
         │   │                                │ │ PARALLEL
         │   └─ E19 /trust/score  ───────────│─┘
         │       │                            │
         │  ⑤ E3+E13 audit (fire-and-forget) │
         │                                    │
         └─────────────────┬─────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Response   │
                    │  {response, │
                    │   intent,   │
                    │   sources,  │
                    │   trust,    │
                    │   anomaly,  │
                    │   degraded} │
                    └─────────────┘
```

**Step details:**

| Step | Engine | Endpoint | Timeout | Fallback on Failure |
|------|--------|----------|---------|---------------------|
| ① | E7 (Neural Network) | `POST /ai/intent` | 15s | Default intent = "general", continue pipeline |
| ② | E6 (Vector DB) | `POST /vectors/search` | 15s | Empty context_passages, fallback to direct chat |
| ③ | E7 (Neural Network) | `POST /ai/rag` or `/ai/chat` | 20s | **Pipeline fails** — return error to client |
| ④a | E8 (Anomaly Detection) | `POST /anomaly/check` | 15s | Skip, mark as degraded |
| ④b | E19 (Trust Scoring) | `POST /trust/score` | 15s | Skip, mark as degraded |
| ⑤ | E3 + E13 | `POST /raw-data/events` + `/analytics/event` | 15s | Logged, never blocks response |

### Graph B: User Onboarding (`POST /api/v1/onboard`)

```
  ① E1 /auth/register ──► user_id, tokens
       │
  ② E2 /identity/create ──► identity_token
       │
  ③ E4 /metadata/process ──► normalized profile
       │
  ④ E5 /processed-metadata/store ──► stored
       │
  ⑤┬─ E15 /eligibility/check ──► verdicts  ─┐
   │                                          │ PARALLEL
   └─ E16 /deadlines/check ──► alerts ───────┘
       │
  ⑥ E12 /profile/generate ──► complete profile
       │
  ⑦ E3+E13 audit (fire-and-forget)
```

**Step details:**

| Step | Engine | Endpoint | Critical? | Fallback |
|------|--------|----------|-----------|----------|
| ① | E1 | `POST /auth/register` | **YES** — aborts if fails | HTTP 500 with registration error |
| ② | E2 | `POST /identity/create` | No | Mark degraded, continue |
| ③ | E4 | `POST /metadata/process` | No | Skip normalization, use raw fields |
| ④ | E5 | `POST /processed-metadata/store` | No | Mark degraded, continue |
| ⑤a | E15 | `POST /eligibility/check` | No | Skip eligibility results |
| ⑤b | E16 | `POST /deadlines/check` | No | Skip deadline alerts |
| ⑥ | E12 | `POST /profile/generate` | No | Skip profile generation |
| ⑦ | E3+E13 | Audit | No | Logged, never blocks |

### Graph C: Policy Ingestion (`POST /api/v1/ingest-policy`)

```
  ① E11 /schemes/fetch ──► raw document text
       │
  ② E21 /documents/parse ──► extracted fields
       │
  ③ E10 /chunks/create ──► chunk array
       │
  ④ E7 /ai/embeddings ──► embedding vectors
       │
  ⑤ E6 /vectors/upsert/batch ──► indexed
       │
  ⑥ E4 /metadata/process ──► tagged
       │
  ⑦ E3+E13 audit
```

**Strict sequential** — each step depends on the previous output.

### Graph D: Voice Query (`POST /api/v1/voice-query`)

```
  ① E7 /ai/intent ──► intent classification
       │
  ②┬── intent=eligibility → E15 /eligibility/check
   ├── intent=scheme_query → E6 /vectors/search → E7 /ai/rag
   ├── intent=deadline → E16 /deadlines/check
   └── intent=general → E7 /ai/chat
       │
  ③ E7 /ai/translate (if language ≠ English)
       │
  ④ E20 /speech/tts ──► audio
       │
  ⑤ E3+E13 audit
```

### Graph E: Eligibility + Explanation (`POST /api/v1/check-eligibility`)

```
  ① E15 /eligibility/check ──► verdicts (DETERMINISTIC — no LLM)
       │
  ② E7 /ai/summarize ──► human-readable explanation (OPTIONAL)
       │
  ③ E3+E13 audit
```

### Graph F: Simulation + Explanation (`POST /api/v1/simulate`)

```
  ① E17 /simulate/what-if ──► before/after/delta (DETERMINISTIC)
       │
  ② E7 /ai/summarize ──► explanation (OPTIONAL)
       │
  ③ E3+E13 audit
```

---

## 3️⃣ Appendix A Resolution

All 5 Appendix A issues from `orchestra-formation.md` have been resolved:

### Issue 1: Dashboard Engine Port Attribute Names ✅ FIXED

**File:** `dashboard-interface/main.py` line ~253  
**Problem:** References like `settings.LOGIN_REGISTER_ENGINE_PORT`, `settings.PROCESSED_METADATA_STORE_PORT`, `settings.NEURAL_NETWORK_ENGINE_PORT` etc. do not exist in `shared/config.py`.  
**Fix:** Replaced all 12 incorrect attribute names with correct names from `shared/config.py`:

| Before (WRONG) | After (CORRECT) |
|---|---|
| `LOGIN_REGISTER_ENGINE_PORT` | `LOGIN_REGISTER_PORT` |
| `PROCESSED_METADATA_STORE_PORT` | `PROCESSED_METADATA_PORT` |
| `NEURAL_NETWORK_ENGINE_PORT` | `NEURAL_NETWORK_PORT` |
| `ANOMALY_DETECTION_ENGINE_PORT` | `ANOMALY_DETECTION_PORT` |
| `POLICY_FETCHING_ENGINE_PORT` | `POLICY_FETCHING_PORT` |
| `JSON_USER_INFO_GENERATOR_PORT` | `JSON_USER_INFO_PORT` |
| `DASHBOARD_INTERFACE_PORT` | `DASHBOARD_BFF_PORT` |
| `ELIGIBILITY_RULES_ENGINE_PORT` | `ELIGIBILITY_RULES_PORT` |
| `DEADLINE_MONITORING_ENGINE_PORT` | `DEADLINE_MONITORING_PORT` |
| `GOVERNMENT_DATA_SYNC_ENGINE_PORT` | `GOV_DATA_SYNC_PORT` |
| `TRUST_SCORING_ENGINE_PORT` | `TRUST_SCORING_PORT` |
| `SPEECH_INTERFACE_ENGINE_PORT` | `SPEECH_INTERFACE_PORT` |
| `DOCUMENT_UNDERSTANDING_ENGINE_PORT` | `DOC_UNDERSTANDING_PORT` |

**Result:** `/dashboard/engines/status` endpoint no longer crashes with `AttributeError`.

### Issue 2: Missing EventType Enum Values ✅ FIXED

**File:** `shared/models.py`  
**Problem:** 9 engines published events using `EventType` values not in the enum, causing Pydantic validation errors.  
**Fix:** Added 10 new event types to the `EventType` enum:

| New EventType | Used By |
|---|---|
| `DOCUMENT_FETCHED` | Policy Fetching Engine (E11) |
| `DOCUMENT_UPDATED` | Policy Fetching Engine (E11) |
| `DOCUMENT_PARSED` | Document Understanding Engine (E21) |
| `CHUNKS_CREATED` | Chunks Engine (E10) |
| `ELIGIBILITY_CHECKED` | Eligibility Rules Engine (E15) |
| `DEADLINE_APPROACHING` | Deadline Monitoring Engine (E16) |
| `SIMULATION_RUN` | Simulation Engine (E17) |
| `AI_QUERY_PROCESSED` | Neural Network (E7), Speech Interface (E20) |
| `TRUST_SCORE_UPDATED` | Trust Scoring Engine (E19) |
| `PROFILE_GENERATED` | JSON User Info Generator (E12) |

**Result:** All engines can publish events without Pydantic validation errors.

### Issue 3: In-Process Event Bus Limitation ✅ MITIGATED

**Problem:** `LocalEventBus` is per-process. E3, E10, E13 subscribe to events but never receive cross-process events.  
**Mitigation:** The orchestrator explicitly calls E3 and E13 via HTTP after every composite pipeline step. This is implemented in the `audit_log()` helper function which fire-and-forget POSTs to both engines. The E11→E21→E10 ingestion pipeline is chained via sequential HTTP calls in the `ingest-policy` composite route, not via events.

**No code change needed in engines.** This is an architectural mitigation, not a fix.

### Issue 4: Simulation Engine Rule Duplication ✅ ACCEPTED FOR MVP

**Problem:** E17 has its own `SCHEME_RULES` dict duplicated from E15.  
**Decision:** Accepted for MVP. Both engines serve different purposes:
- E15: Evaluates real eligibility (source of truth)
- E17: Runs what-if simulations (isolation is a feature)

The `POST /api/v1/simulate` composite route chains E17 with an optional E7 explanation but does NOT call E15. This preserves simulation isolation.

**Future fix:** Both engines should read from `eligibility_rules` DB table (E15 already seeds it).

### Issue 5: Missing Gateway Proxy Routes ✅ FIXED

**File:** `api-gateway/routes.py`  
**Problem:** 5 engines had no proxy routes through the gateway.  
**Fix:** Added 6 new proxy route groups (5 originally missing + Gov Data Sync):

| Route | Engine | Port | Methods |
|---|---|---|---|
| `/api/v1/raw-data/{path:path}` | Raw Data Store (E3) | 8003 | GET, POST |
| `/api/v1/processed-metadata/{path:path}` | Processed Metadata (E5) | 8005 | GET, POST, PUT, DELETE |
| `/api/v1/vectors/{path:path}` | Vector Database (E6) | 8006 | GET, POST, DELETE |
| `/api/v1/anomaly/{path:path}` | Anomaly Detection (E8) | 8008 | GET, POST, PUT |
| `/api/v1/chunks/{path:path}` | Chunks Engine (E10) | 8010 | GET, POST |
| `/api/v1/gov-data/{path:path}` | Gov Data Sync (E18) | 8018 | GET, POST |

**Result:** All 21 engines are now reachable through the API Gateway. Total proxy routes: 21.

---

## 4️⃣ LLM Enforcement Mechanism

The LLM boundary is enforced at three levels:

### Level 1: Architectural Separation

Deterministic engines (E8, E15, E16, E17, E19) **do not import** `nvidia_client`. They have zero dependency on NVIDIA NIM. A code-level grep confirms:

```
grep -r "nvidia_client" eligibility-rules-engine/ → NO RESULTS
grep -r "nvidia_client" simulation-engine/         → NO RESULTS
grep -r "nvidia_client" anomaly-detection-engine/  → NO RESULTS
grep -r "nvidia_client" deadline-monitoring-engine/ → NO RESULTS
grep -r "nvidia_client" trust-scoring-engine/      → NO RESULTS
```

These engines **cannot** call the LLM even if instructed to.

### Level 2: Orchestrator Route Design

Each composite route hardcodes which steps use LLM and which don't:

| Route | Deterministic Steps | LLM Steps |
|---|---|---|
| `/api/v1/query` | Vector search (E6), Anomaly check (E8), Trust score (E19) | Intent (E7), RAG/Chat (E7) |
| `/api/v1/onboard` | **ALL 7 steps** — Register, Identity, Metadata, Store, Eligibility, Deadlines, Profile | NONE |
| `/api/v1/check-eligibility` | Eligibility check (E15) | Explanation only (E7, optional) |
| `/api/v1/ingest-policy` | Fetch (E11), Chunk (E10), Upsert (E6), Tag (E4) | Parse (E21), Embed (E7) |
| `/api/v1/voice-query` | Eligibility routing (E15), Deadline routing (E16) | Intent (E7), Chat (E7), Translate (E7), TTS (E20) |
| `/api/v1/simulate` | Simulation (E17) | Explanation only (E7, optional) |

### Level 3: LLM Guardrails in Neural Network Engine (E7)

- **System prompt isolation:** User input never placed in system prompt slot
- **Context grounding:** RAG responses grounded in retrieved chunks, not hallucinated
- **Temperature control:** 0.3 for factual queries, 0.7 for conversational
- **Token limit:** `max_tokens=1024` prevents runaway generation
- **Model rotation:** Three NVIDIA API keys with automatic rotation on 429

### Prohibited Actions (Enforced by Architecture)

| Action | Enforced By |
|---|---|
| LLM determines eligibility verdict | E15 has no NIM import |
| LLM computes trust scores | E19 has no NIM import |
| LLM detects anomalies | E8 has no NIM import |
| LLM modifies user data | No E2/E4/E5 calls from E7 |
| LLM makes scheduling decisions | E16 has no NIM import |
| LLM generates simulation results | E17 has no NIM import |
| LLM decides orchestration routing | Orchestrator uses deterministic if/else |

---

## 5️⃣ Failure Containment Strategy

### Circuit Breaker Implementation

The orchestrator includes a per-engine circuit breaker (`CircuitBreaker` class in `orchestrator.py`):

```
States: CLOSED → OPEN → HALF_OPEN → CLOSED

CLOSED (normal):
  Forward all requests.
  Track consecutive failures per engine.

OPEN (tripped):
  After 5 consecutive failures → reject immediately with 503.
  No HTTP call made to failing engine.
  Duration: 30 seconds.

HALF_OPEN (probe):
  After 30s, allow 1 request through.
  If success → CLOSED (reset counter).
  If failure → OPEN (reset timer).
```

**Monitoring:** `GET /api/v1/circuit-breaker/status` returns per-engine state:
```json
{
  "neural_network": {"state": "closed", "failures": 0},
  "vector_database": {"state": "open", "failures": 5},
  "eligibility_rules": {"state": "half_open", "failures": 5}
}
```

### Degraded Response Pattern

Every composite route tracks a `degraded: list[str]` that records which sub-steps failed. The response always includes available data:

```json
{
  "success": true,
  "data": {
    "response": "Based on your profile...",
    "intent": "general",
    "sources": [],
    "trust": {},
    "anomaly": {},
    "degraded": ["vector_search", "anomaly_check"]
  }
}
```

**Client contract:** When `degraded` is not null, some data may be missing. The client can show a banner: "Some features are temporarily unavailable."

### Failure Impact Matrix

| Engine Down | Impact on `query` | Impact on `onboard` | Impact on `ingest-policy` | Impact on `voice-query` |
|---|---|---|---|---|
| E7 (Neural Network) | ❌ Pipeline fails | ✅ No impact (no LLM) | ⚠️ No embeddings | ❌ No response gen |
| E6 (Vector DB) | ⚠️ No context passages → direct chat | ✅ No impact | ⚠️ No vector upsert | ⚠️ No RAG context |
| E8 (Anomaly) | ⚠️ Skip anomaly check | ✅ No impact | ✅ No impact | ✅ No impact |
| E15 (Eligibility) | ✅ No impact | ⚠️ Skip eligibility | ✅ No impact | ⚠️ Skip if routed |
| E19 (Trust) | ⚠️ Skip trust score | ✅ No impact | ✅ No impact | ✅ No impact |
| E1 (Login/Register) | ✅ No impact | ❌ Onboarding fails | ✅ No impact | ✅ No impact |
| E3 (Raw Data) | ⚠️ No audit log | ⚠️ No audit log | ⚠️ No audit log | ⚠️ No audit log |
| E13 (Analytics) | ⚠️ No analytics event | ⚠️ No analytics event | ⚠️ No analytics event | ⚠️ No analytics event |

Legend: ❌ = route fails, ⚠️ = degraded but functional, ✅ = unaffected

### Error Propagation Rules

```
Engine-level errors → try/catch with EngineCallError
  ├─ 503 (ConnectError)  → circuit breaker failure recorded
  ├─ 504 (Timeout)       → circuit breaker failure recorded
  ├─ 4xx (client error)  → propagated with engine detail
  └─ 5xx (server error)  → propagated with engine detail

Audit failures → NEVER block the response
  └─ asyncio.create_task() for fire-and-forget

Critical step failures → HTTPException to client
  └─ Only registration (E1 in onboard) and primary engine in each route

Non-critical step failures → degraded[] annotation
  └─ Everything else: identity, metadata, anomaly, trust, explanation
```

---

## 6️⃣ Idempotency Preservation

### Idempotent Operations (Safe to Retry)

| Operation | Mechanism | Retry Policy |
|---|---|---|
| Vector search (E6) | Query-only, no mutation | Retry 1x on timeout |
| Eligibility check (E15) | Pure function of profile + rules | Retry 1x on timeout |
| Anomaly check (E8) | Pure function of input data | Retry 1x on timeout |
| Trust scoring (E19) | Pure function of signals | Retry 1x on timeout |
| Intent classification (E7) | Stateless classification | Retry 1x on timeout |
| Deadline check (E16) | Read-only date arithmetic | Retry 1x on timeout |
| Health probes | Read-only GET | Retry 1x on timeout |

### Non-Idempotent Operations (NEVER Retry)

| Operation | Why Not Retry | Safeguard |
|---|---|---|
| User registration (E1) | Creates duplicate user | `call_engine()` does NOT retry by default |
| Identity creation (E2) | Creates duplicate vault entry | Single call, fail-open |
| Metadata store (E5) | Overwrites processed metadata | Single call, fail-open |
| RAG generation (E7) | Token consumption, conversation log | Single call |
| Policy fetch (E11) | External HTTP to source → content hash prevents duplication | E11's own hash-based dedup |
| Vector upsert (E6) | `chunk_id` uniqueness prevents duplication | E6's own dedup |
| Audit log (E3) | `event_id` UUID prevents exact duplication | Single fire-and-forget |

### Idempotency Keys

The orchestrator propagates `X-Request-ID` through all chained calls. This enables:
- **Deduplication at audit level:** E3 can detect duplicate audit entries with same correlation ID
- **End-to-end tracing:** Every log line includes the request ID
- **Replay detection:** If the same request is retried with the same ID, downstream engines can detect it

---

## 7️⃣ Scalability Stress Validation

### Current MVP Limits

| Component | Bottleneck | Practical Limit | Workaround |
|---|---|---|---|
| SQLite | Single-writer lock (WAL mode helps readers) | ~100 concurrent writes/sec | Queue writes; PostgreSQL swap changes only `DATABASE_URL` |
| In-memory Vector Index (E6) | RAM | ~100K vectors in 1GB RAM | Disk-backed HNSW (hnswlib supports) |
| NVIDIA NIM API | 3 API keys, rate-limited | ~60 RPM per key = 180 RPM total | Queue, backpressure at gateway |
| LocalEventBus | Per-process, in-memory | No cross-engine events | Orchestrator HTTP calls replace events |
| Circuit Breaker | In-memory, single gateway | If gateway restarts, state is lost | Acceptable for MVP; Redis-backed CB for prod |

### Scale Path: Vertical (Same Machine)

| Change | Config Diff | Code Changes |
|---|---|---|
| SQLite → PostgreSQL | `DATABASE_URL=postgresql+asyncpg://...` | **ZERO** — SQLAlchemy abstraction |
| Enable Redis cache | `USE_REDIS=True`, `REDIS_URL=redis://...` | **ZERO** — `LocalCache` has Redis branch |
| Enable Redis event bus | Swap `shared/event_bus.py` implementation | **ZERO** engine changes — same `publish()`/`subscribe()` interface |
| Multiple uvicorn workers | `uvicorn --workers 4` per engine | **ZERO** — stateless engines |

### Scale Path: Horizontal (Multi-Machine)

| Change | Engine Code Changes | Shared Code Changes |
|---|---|---|
| Docker per engine | ZERO — add Dockerfile only | ZERO |
| K8s services | ZERO — swap `ENGINE_URLS` to K8s DNS names | Change `localhost` to service names in config |
| Distributed vector DB | E6 internal swap to Milvus/Qdrant | ZERO for orchestrator |
| Redis Streams event bus | ZERO for engines | Swap `shared/event_bus.py` to Redis Streams |

### Anti-Patterns Validated ✅

```
✅ No engine imports from another engine's codebase
✅ No hardcoded localhost URLs in engine code (all via ENGINE_URLS)
✅ No global mutable singletons shared across processes
✅ No file-based locking between engines
✅ No engine-to-engine direct HTTP calls (only gateway)
✅ No shared in-memory state across processes
✅ Orchestrator routes are stateless (circuit breaker state is volatile)
```

---

## 8️⃣ Implementation Blueprint (Pseudocode → Real Code)

### Files Created / Modified

| File | Action | Purpose |
|---|---|---|
| `api-gateway/orchestrator.py` | **CREATED** | Orchestrator module: CircuitBreaker, call_engine(), audit_log(), 6 composite routes, 2 system endpoints |
| `api-gateway/main.py` | **MODIFIED** | Import and register `orchestrator_router` before `gateway_router`; update root route directory |
| `api-gateway/routes.py` | **MODIFIED** | Added 6 proxy route groups for E3, E5, E6, E8, E10, E18 |
| `shared/models.py` | **MODIFIED** | Added 10 missing EventType enum values |
| `dashboard-interface/main.py` | **MODIFIED** | Fixed 13 incorrect port attribute names in `engines_status()` |

### Code Structure — `api-gateway/orchestrator.py`

```
orchestrator.py (710 lines)
│
├── CircuitBreaker class (60 lines)
│   ├── allow_request(engine) → bool
│   ├── record_success(engine)
│   ├── record_failure(engine)
│   └── get_status() → dict
│
├── call_engine() (50 lines)
│   ├── Circuit breaker check
│   ├── httpx.AsyncClient with configurable timeout
│   ├── Request ID propagation
│   ├── ApiResponse envelope unwrapping
│   └── EngineCallError on failure
│
├── EngineCallError class (10 lines)
│
├── audit_log() (20 lines)
│   ├── POST to E3 /raw-data/events
│   ├── POST to E13 /analytics/event
│   └── asyncio.create_task (fire-and-forget)
│
├── Request/Response schemas (60 lines)
│   ├── QueryRequest, OnboardRequest
│   ├── IngestPolicyRequest, VoiceQueryRequest
│   ├── EligibilityRequest, SimulateRequest
│
├── POST /api/v1/query (90 lines)
│   └── Intent → Vector → RAG → Anomaly∥Trust → Audit
│
├── POST /api/v1/onboard (130 lines)
│   └── Register → Identity → Meta → Store → Elig∥Deadline → Profile → Audit
│
├── POST /api/v1/check-eligibility (50 lines)
│   └── Eligibility → optional Explain → Audit
│
├── POST /api/v1/ingest-policy (120 lines)
│   └── Fetch → Parse → Chunk → Embed → Upsert → Tag → Audit
│
├── POST /api/v1/voice-query (100 lines)
│   └── Intent → Route → Translate → TTS → Audit
│
├── POST /api/v1/simulate (50 lines)
│   └── Simulate → optional Explain → Audit
│
├── GET /api/v1/circuit-breaker/status (5 lines)
│
└── GET /api/v1/engines/health (20 lines)
    └── Parallel health probe to all 20 engines
```

### Key Implementation Details

**`call_engine()` — Core HTTP Helper:**
```python
async def call_engine(engine_key, path, payload, method="POST", request_id="", timeout=15.0):
    # 1. Check circuit breaker → if OPEN, raise immediately (no HTTP call)
    # 2. Build URL from ENGINE_URLS[engine_key] + path
    # 3. httpx.AsyncClient(timeout=timeout) → JSON request
    # 4. Record success/failure in circuit breaker
    # 5. Unwrap ApiResponse {"data": {...}} envelope → return inner data
    # 6. On ConnectError/TimeoutException → EngineCallError with 503/504
```

**Parallel Steps (asyncio.gather):**
```python
# Used in /query (anomaly + trust), /onboard (eligibility + deadlines)
results = await asyncio.gather(task_a, task_b, return_exceptions=True)
if isinstance(results[0], Exception):
    degraded.append("step_a")  # Don't crash — degrade gracefully
else:
    data_a = results[0]
```

**Audit (fire-and-forget):**
```python
async def audit_log(event_type, user_id, payload, request_id):
    async def _post():
        await call_engine("raw_data_store", "/raw-data/events", {...})
        await call_engine("analytics_warehouse", "/analytics/event", {...})
    asyncio.create_task(_post())  # Returns immediately, runs in background
```

---

## 9️⃣ Production Readiness Checklist

### 📋 Pre-Test Note: IDE "Import Not Resolved" Warnings

After implementation, the VS Code IDE reports `Import "fastapi" could not be resolved`, `Import "httpx" could not be resolved`, `Import "pydantic" could not be resolved`, etc. across all modified files (`orchestrator.py`, `main.py`, `routes.py`, `models.py`, `dashboard-interface/main.py`).

**These are NOT code errors.** They are the IDE's Python language server (Pylance) failing to locate packages because the workspace Python environment / venv is not configured in VS Code settings. All packages (`fastapi`, `httpx`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `aiosqlite`, `uvicorn`, `bcrypt`, `python-jose`, `cryptography`, `openai`) are installed and verified working — every one of the 21 engines started and passed health checks during Phase 4 testing (see `1st-engine-tests.md`).

**Evidence:** Phase 4 achieved 21/21 engines healthy on their respective ports. No import errors occurred at runtime. The IDE warnings can be resolved by selecting the correct Python interpreter in VS Code (`Ctrl+Shift+P → Python: Select Interpreter → choose the venv or system Python where packages are installed`), but this is a developer tooling configuration issue, not a code defect.

**Action for testers:** Ignore Pylance/IDE import warnings. If engines start with `uvicorn`, the imports are resolved correctly at runtime.

---

### ✅ Implemented (Ready for Testing)

| Item | Status | Evidence |
|---|---|---|
| Orchestrator module with 6 composite routes | ✅ | `api-gateway/orchestrator.py` |
| Circuit breaker per engine | ✅ | `CircuitBreaker` class, `GET /api/v1/circuit-breaker/status` |
| Degraded response pattern | ✅ | Every composite route has `degraded: list[str]` |
| X-Request-ID propagation | ✅ | `call_engine()` forwards `request_id` in headers |
| Audit trail for every composite flow | ✅ | `audit_log()` fire-and-forget to E3 + E13 |
| JWT authentication on protected routes | ✅ | `require_auth` dependency on all routes (except `/onboard`, `/voice-query`) |
| Missing proxy routes for 6 engines | ✅ | E3, E5, E6, E8, E10, E18 now accessible via gateway |
| Dashboard port attribute fix | ✅ | 13 attributes corrected |
| EventType enum completeness | ✅ | 10 new values added, 42 total |
| LLM boundary enforcement | ✅ | Architectural separation (no NIM import in deterministic engines) |
| Parallel execution where safe | ✅ | `asyncio.gather` for anomaly+trust, eligibility+deadlines |
| Timeout hierarchy | ✅ | Gateway 30s > Engine 15s > LLM 20s (configurable per call) |

### ⚠️ Requires Integration Testing

| Item | Test Plan |
|---|---|
| End-to-end RAG query | Start E0, E6, E7, E8, E19, E3; POST /api/v1/query |
| End-to-end onboarding | Start E0, E1, E2, E4, E5, E15, E16, E12, E3; POST /api/v1/onboard |
| Policy ingestion | Start E0, E11, E21, E10, E7, E6, E4, E3; POST /api/v1/ingest-policy |
| Voice query | Start E0, E7, E6, E15, E16, E20, E3; POST /api/v1/voice-query |
| Circuit breaker tripping | Stop E7, send 5 requests, verify E7 circuit opens |
| Partial failure degradation | Stop E8, send /query, verify response has `degraded: ["anomaly_check"]` |
| Dashboard engines/status | Start E14, verify /dashboard/engines/status returns 200 (not 500) |

### 🔮 Future Improvements (Post-MVP)

| Item | Priority | Effort |
|---|---|---|
| Redis-backed circuit breaker | Medium | Low — persist state to Redis |
| Retry with exponential backoff for idempotent calls | Medium | Low — add to `call_engine()` |
| OpenTelemetry distributed tracing | High | Medium — add spans per engine call |
| Rate limiting per composite route | Medium | Low — extend `RateLimitMiddleware` |
| WebSocket streaming for `/query` | High | Medium — stream E7 tokens |
| Background job queue for `/ingest-policy` | High | Medium — Celery or asyncio task queue |
| E15/E17 rule synchronization via DB | Low | Low — both read from `eligibility_rules` table |
| Redis event bus replacing LocalEventBus | Medium | Low — swap `shared/event_bus.py` |
| PostgreSQL migration | High (for scale) | Low — change `DATABASE_URL` only |

---

## Appendix: Complete Route Registry (Post-Implementation)

### Composite Routes (Orchestrator)

| Method | Path | Auth | Type |
|---|---|---|---|
| POST | `/api/v1/query` | Required | Agent (RAG pipeline) |
| POST | `/api/v1/onboard` | None (creates user) | Controller |
| POST | `/api/v1/check-eligibility` | Required | Controller + optional LLM |
| POST | `/api/v1/ingest-policy` | Required | Controller |
| POST | `/api/v1/voice-query` | Optional | Agent (voice pipeline) |
| POST | `/api/v1/simulate` | Required | Controller + optional LLM |
| GET | `/api/v1/circuit-breaker/status` | Required | System |
| GET | `/api/v1/engines/health` | Required | System |

### Proxy Routes (Direct Pass-Through)

| Method | Path Prefix | Target Engine | Port |
|---|---|---|---|
| ALL | `/api/v1/auth/*` | Login/Register (E1) | 8001 |
| ALL | `/api/v1/identity/*` | Identity (E2) | 8002 |
| ALL | `/api/v1/raw-data/*` | Raw Data Store (E3) | 8003 |
| ALL | `/api/v1/metadata/*` | Metadata (E4) | 8004 |
| ALL | `/api/v1/processed-metadata/*` | Processed Metadata (E5) | 8005 |
| ALL | `/api/v1/vectors/*` | Vector Database (E6) | 8006 |
| ALL | `/api/v1/ai/*` | Neural Network (E7) | 8007 |
| ALL | `/api/v1/anomaly/*` | Anomaly Detection (E8) | 8008 |
| ALL | `/api/v1/chunks/*` | Chunks Engine (E10) | 8010 |
| ALL | `/api/v1/schemes/*` | Policy Fetching (E11) | 8011 |
| ALL | `/api/v1/policies/*` | Policy Fetching (E11) | 8011 |
| ALL | `/api/v1/profile/*` | JSON User Info (E12) | 8012 |
| ALL | `/api/v1/analytics/*` | Analytics Warehouse (E13) | 8013 |
| ALL | `/api/v1/dashboard/*` | Dashboard BFF (E14) | 8014 |
| ALL | `/api/v1/eligibility/*` | Eligibility Rules (E15) | 8015 |
| ALL | `/api/v1/deadlines/*` | Deadline Monitoring (E16) | 8016 |
| ALL | `/api/v1/simulate/*` | Simulation (E17) | 8017 |
| ALL | `/api/v1/gov-data/*` | Gov Data Sync (E18) | 8018 |
| ALL | `/api/v1/trust/*` | Trust Scoring (E19) | 8019 |
| ALL | `/api/v1/voice/*` | Speech Interface (E20) | 8020 |
| ALL | `/api/v1/documents/*` | Doc Understanding (E21) | 8021 |

**Total: 8 composite routes + 21 proxy route groups = 29 route groups through a single gateway on port 8000.**

---

*Document generated: February 28, 2026*  
*Implementation version: 1.0*  
*All code changes committed. Ready for integration testing.*
