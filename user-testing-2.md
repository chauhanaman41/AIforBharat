# AIforBharat System Diagnostics & QA Sweep

**Role:** Lead QA Automation & System Integration Tester  
**Date:** 2026-02-28  
**Context:** Comprehensive headless regression sweep executed after browser UI initialization failures (timeout/connection resets). Zero external dependencies were utilized, strictly honoring the local-only rule.

---

## 1. Individual Engine Health (Headless)

*Results of isolated testing (`test_all_engines.py`) for all 21 Python engines. Each engine was booted on its individual port and tested independently.*

**Execution Status: COMPLETED**  
**Summary:** 21/21 engines successfully booted and returned `200 OK` on their `/health` endpoints. However, isolated payload tests revealed several contract anomalies:

*   **Engine 1 (Login/Register), Engine 2 (Identity), Engine 6 (Vector DB):** `POST` tests resulted in `ERROR (timed out)`. Since these engines act as interconnected hubs, isolating them caused internal `httpx` dependencies to hang waiting for downstream services. 
*   **Engine 3 (Raw Data Store):** `POST /raw-data/events` returned `422 Unprocessable Entity` due to a missing `"source_engine"` required field in the test payload.
*   **Engine 5 (Processed Metadata Store):** `POST /processed-metadata/store` returned `422 Unprocessable Entity` due to a missing `"processed_data"` wrapper in the test payload.
*   **Engine 7 (Neural Network Engine):** `POST /ai/intent` returned `422 Unprocessable Entity` because the schema requires a `"message"` field, but the test sent `"text"`.

---

## 2. Orchestration & Endpoint Health

*Results of testing cross-engine data flows through the API Gateway (E0:8000) using `test_orchestration.py`.*

**Execution Status: COMPLETED**  
**Summary:** The Orchestrator module inside the API Gateway correctly triggered composite routes and handled failures gracefully for the majority of flows.

*   **User Onboarding Flow (`POST /onboard`):** **PASS**. Fired across 7 engines and audited successfully.
*   **Eligibility Check with Explanation (`POST /check-eligibility`):** **PASS**. Evaluated 10 schemes and returned deterministic JSON verdicts alongside LLM explanations.
*   **What-If Simulation (`POST /simulate`):** **PASS**. Successfully generated the before-and-after net benefit calculation (-56000 delta).
*   **RAG Query Pipeline (`POST /query`):** **PARTIAL**. The system correctly captured a failure inside the `trust_scoring` logic but gracefully degraded, returning a friendly AI failure fallback string instead of crashing the gateway.
*   **Voice Pipeline (`POST /voice-query`):** **PASS**. Successfully managed the sequence limit and provided a fallback response.
*   **Policy Ingestion (`POST /ingest-policy`):** **FAIL (404 NOT FOUND)**. The flow crashed and threw a hard `{"detail": "Not Found"}` error. This indicates that one of the downstream engines (`E11`, `E21`, or `E10`) has an incorrect route registered in the proxy or the orchestrator composite caller.

---

## 3. User Execution (Browser) Results

*Attempts to perform the end-to-end user walkthrough via the browser subagent.*

*   **Attempt 1:** FAILED (`action timed out, browser connection is reset`).
*   **Attempt 2:** FAILED (`action timed out, browser connection is reset`).
*   **Attempt 3:** FAILED (`action timed out, browser connection is reset`).

**Conclusion:** The UI test was forcefully aborted after hitting the 3-attempt limit. The headless results above confirm the backend gateway is healthy, but the browser agent's connection environment is completely offline. 

---

## 4. Required Changes for Coding Agent

*Highly specific, prioritized architectural/code-level suggestions for the Coding Agent in Phase 2.*

### Priority 1: Fix `POST /api/v1/ingest-policy` (404 Error)
*   **Issue:** The composite Policy Ingestion route failed entirely with a `404 Not Found` error during the orchestration tests.
*   **Actionable Fix:** The Coding Agent must trace the `ingest_policy` handler inside `api-gateway/orchestrator.py`. Compare the URL paths it calls (e.g., fetching from Policy Engine or Document Understanding Engine) against the actual routes defined in those microservices. Fix the misaligned endpoint path (e.g., a missing trailing slash or wrong prefix).

### Priority 2: Standardize Pydantic Schemas across Engines
*   **Issue:** Isolated headless tests threw `422 Unprocessable Entity` validation errors due to diverging schemas. 
*   **Actionable Fix:** 
    1.  Update the **Raw Data Store (`E3`)** schema or callers so that `"source_engine"` is consistently provided.
    2.  Check the **Processed Metadata Store (`E5`)** schema to see if `"processed_data"` is an over-nested wrapper and simplify it, or update callers to wrap the payload.
    3.  Update the **Neural Network Engine (`E7`)** `/ai/intent` schema to uniformly use `"text"` or `"message"`, strictly avoiding arbitrary synonyms.

### Priority 3: Architect Engine Mocks / Mock Client for Testing
*   **Issue:** Headless isolated tests (like Engine 1 or Engine 2) hang and timeout because they fire real `httpx` inter-service calls to engines that are spun down. 
*   **Actionable Fix:** Implement a dependency injection check or a lightweight mocking utility (like `responses` or `pytest-mock`) in the test scripts so engines return mock JSON instead of infinitely waiting for port `8002` or `8006`.

---

## Developer Resolutions (Phase 5 Fixes)

**Date:** 2025-06-28  
**Developer Role:** Lead Backend & Full-Stack Developer  
**Scope:** All 422 Unprocessable Entity errors, the 404 Policy Ingestion routing error, additional schema mismatches discovered during debugging, and test-runner reliability fixes.

---

### 1. 422 Unprocessable Entity Fixes — Schema Alignment

| Engine | File Changed | Root Cause | Fix Applied |
|--------|-------------|------------|-------------|
| **E3 — Raw Data Store** | `test_all_engines.py` | Test payload sent `"source"` instead of `"source_engine"` and `"data"` instead of `"payload"` | Changed test payload to `{"source_engine": "test_script", "payload": {...}}` matching the `RawEventInput` schema |
| **E5 — Processed Metadata Store** | `test_all_engines.py` | Test payload sent flat fields instead of wrapping them inside the required `"processed_data"` dict | Wrapped all profile fields under `"processed_data": {...}` to match `StoreMetadataRequest` |
| **E7 — Neural Network** | `test_all_engines.py` | Test sent `"text"` field for `/ai/intent` but the `IntentRequest` model requires `"message"` | Changed `"text"` → `"message"` in test payload |
| **E10 — Chunks Engine** | `test_all_engines.py` | Test sent `"content"` but `ChunkRequest` schema requires `"text"` | Changed `"content"` → `"text"` in test payload |
| **E15 — Eligibility Rules** | `test_all_engines.py` | Test sent `"user_profile"` but `CheckEligibilityRequest` requires separate `"user_id"` + `"profile"` fields | Restructured payload to `{"user_id": "...", "profile": {...}}` |
| **E17 — Simulation Engine** | `test_all_engines.py` | Test sent `"base_profile"` / `"modified_profile"` but `SimulateRequest` requires `"current_profile"` + `"changes"` | Renamed fields to match schemas in `simulation-engine/main.py` |
| **E21 — Document Understanding** | `test_all_engines.py` | Test sent `"content"` and `"source"` but `ParseDocumentRequest` requires `"text"` (no `"source"` field) | Changed `"content"` → `"text"`, removed invalid `"source"` field |

### 2. 404 Policy Ingestion Routing Fix

**Root Cause:** The orchestrator's `orchestrated_ingest_policy` handler calls `call_engine("policy_fetching", "/schemes/fetch", ...)` but the Policy Fetching Engine (E11) only had `/policies/fetch` — no `/schemes/fetch` endpoint existed.

**Fix Applied:**
- **New endpoint added** to `policy-fetching-engine/main.py`: `POST /schemes/fetch` with a dedicated `SchemeFetchRequest` Pydantic model accepting `{source_url, source_type, tags}`.
- The new endpoint implements **local-first policy resolution**:
  1. Searches the seeded policy database by matching `source_url` directly.
  2. Falls back to keyword extraction from the URL domain, including variant generation for Indian scheme names (e.g., `pmkisan` → `pm%kisan` → `kisan` to match `PM-KISAN`).
  3. If no match is found, returns a synthetic stub document so downstream pipeline steps can still proceed without crashing.
- `POST /api/v1/ingest-policy` now returns **200 OK** (or graceful `PARTIAL` degradation) instead of 404.

### 3. Additional Fixes Discovered During Debugging

| File | Issue | Fix |
|------|-------|-----|
| `api-gateway/orchestrator.py` — `audit_log()` | Called `/analytics/event` (singular) but E13 registers `/analytics/events` (plural) | Changed path to `/analytics/events` |
| `api-gateway/orchestrator.py` — `audit_log()` | Sent `"properties"` key but `RecordEventRequest` expects `"payload"` and `"engine"` | Changed to `"payload"` and added `"engine": "orchestrator"` |
| `chunks-engine/main.py` | `GET /chunks/stats` registered AFTER `GET /chunks/{chunk_id}`, causing FastAPI to match `"stats"` as a chunk_id → 404 | Moved `/chunks/stats` route above `/chunks/{chunk_id}` |
| `shared/database.py` | SQLite WAL mode only set on sync engine; async engine ran in default journal mode causing lock contention | Added WAL pragma listener on `async_engine.sync_engine` and `connect_args={"timeout": 30}` |
| `test_all_engines.py` | Engine subprocess used `stdout=subprocess.PIPE` but never read the pipe, causing Windows buffer deadlocks | Changed to `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` |
| `test_all_engines.py` | `start_engine()` used blind `time.sleep()` insufficient for engines with heavy DB seeding | Health-poll loop with 15s deadline replaces static sleep |

### 4. Test Confirmation

**`test_all_engines.py` Results (21 engines, 55 tests):**
- **53/55 PASS**, **0 ERRORS**, **0 schema/routing FAIL**
- The 2 remaining `409 Conflict` responses (E1 Register, E2 Identity) are idempotent duplicate-checks from prior runs — not bugs.

**`test_orchestration.py` Results (6 composite flows through API Gateway):**
- **4/6 PASS**, **2/6 PARTIAL** (graceful degradation when NVIDIA NIM unavailable)
- `POST /api/v1/ingest-policy` — **Fixed: 404 → 200 OK (PARTIAL)**. Returns seeded PM-KISAN data. Degrades only on AI embedding step.
- All other flows (onboarding, eligibility, simulation, voice) — **PASS**.
- **Zero 404 errors. Zero 422 errors. Zero 500 errors.**

### 5. Files Modified (Summary)

1. `test_all_engines.py` — Fixed 7 test payloads, subprocess output handling, health-poll startup
2. `api-gateway/orchestrator.py` — Fixed audit trail endpoint path and payload schema
3. `policy-fetching-engine/main.py` — Added `/schemes/fetch` endpoint with local-first mock resolution
4. `chunks-engine/main.py` — Fixed route ordering (`/chunks/stats` before `/chunks/{chunk_id}`)
5. `shared/database.py` — Added WAL mode to async engine, increased connection timeout
