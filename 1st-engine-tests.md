# AIforBharat — 1st Engine Test Report

> **Date:** February 28, 2026  
> **Phase:** Phase 4 — Bug Fixing & Validation  
> **Platform:** Windows, Python 3.11, FastAPI, SQLite (aiosqlite)  
> **Total Engines:** 21 microservices on ports 8000–8021 (8009 unused)

---

## 1. Test Methodology

### How Tests Were Performed

1. **Startup Test:** Each engine was launched individually using:
   ```powershell
   Start-Process python -ArgumentList "-m","uvicorn","<engine-folder>.main:app","--port","<port>" -NoNewWindow -RedirectStandardError "data\err_eX.txt"
   ```
   Then waited 5–8 seconds and inspected stderr output for crash tracebacks.

2. **Health Check:** After startup, every engine's `/health` endpoint was hit:
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:<port>/health" -TimeoutSec 3
   ```
   A 200 OK response = healthy. Connection refused = engine crashed on startup.

3. **Endpoint Schema Validation:** POST endpoints were tested with various JSON payloads to check for 422 (Unprocessable Entity) responses caused by Pydantic schema mismatches between documentation and actual code.

4. **Full Fleet Test:** All 21 engines launched simultaneously, then all 21 `/health` endpoints tested in a loop.

---

## 2. Initial Test Results (Before Fixes)

### 🟢 13 Healthy Engines (startup OK, /health → 200)

| # | Engine | Port | Folder | Status |
|---|--------|------|--------|--------|
| 1 | API Gateway | 8000 | `api-gateway/` | ✅ OK |
| 2 | Login Register | 8001 | `login-register-engine/` | ✅ OK |
| 3 | Identity Engine | 8002 | `identity-engine/` | ✅ OK |
| 4 | Raw Data Store | 8003 | `raw-data-store/` | ✅ OK |
| 7 | Neural Network | 8007 | `neural-network-engine/` | ✅ OK |
| 8 | Anomaly Detection | 8008 | `anomaly-detection-engine/` | ✅ OK |
| 9 | Chunks Engine | 8010 | `chunks-engine/` | ✅ OK |
| 10 | Metadata Engine | 8004 | `metadata-engine/` | ✅ OK |
| 12 | JSON User Info | 8012 | `json-user-info-generator/` | ✅ OK |
| 14 | Dashboard Interface | 8014 | `dashboard-interface/` | ✅ OK |
| 17 | Simulation Engine | 8017 | `simulation-engine/` | ✅ OK |
| 19 | Trust Scoring | 8019 | `trust-scoring-engine/` | ✅ OK |
| 21 | Doc Understanding | 8021 | `document-understanding-engine/` | ✅ OK |

### 🔴 8 Failing Engines (Connection Refused — crash on startup)

| # | Engine | Port | Folder | Status |
|---|--------|------|--------|--------|
| 5 | Processed Metadata Store | 8005 | `processed-user-metadata-store/` | ❌ FAIL |
| 6 | Vector Database | 8006 | `vector-database/` | ❌ FAIL |
| 11 | Policy Fetching | 8011 | `policy-fetching-engine/` | ❌ FAIL |
| 13 | Analytics Warehouse | 8013 | `analytics-warehouse/` | ❌ FAIL |
| 15 | Eligibility Rules | 8015 | `eligibility-rules-engine/` | ❌ FAIL |
| 16 | Deadline Monitoring | 8016 | `deadline-monitoring-engine/` | ❌ FAIL |
| 18 | Gov Data Sync | 8018 | `government-data-sync-engine/` | ❌ FAIL |
| 20 | Speech Interface | 8020 | `speech-interface-engine/` | ❌ FAIL |

### ⚠️ 422 Schema Mismatches Identified

| Endpoint | Expected Payload | Actual Required Payload | Issue |
|----------|-----------------|------------------------|-------|
| `POST /raw-data/events` | `{"event_type":"...","source":"...","data":{}}` | `{"event_type":"...","source_engine":"...","payload":{}}` | Field names differ: `source` → `source_engine`, `data` → `payload` |
| `POST /ai/intent` | `{"text":"..."}` | `{"message":"..."}` | Field name: `text` → `message` |
| `POST /simulate/what-if` | `{"base_profile":{}, "modified_profile":{}}` | `{"user_id":"...","current_profile":{}, "changes":{}}` | Completely different structure with `current_profile` wrapper |

---

## 3. Debugging Process — Engine by Engine

### Engine 5 — Processed Metadata Store (Port 8005)

**Investigation:**
```powershell
Start-Process python -ArgumentList "-m","uvicorn","processed-user-metadata-store.main:app","--port","8005" `
  -NoNewWindow -RedirectStandardError "data\err_e5.txt"
```

**Finding:** Engine started **successfully**. Tables `user_metadata`, `user_derived_attributes`, `user_eligibility_cache`, `user_risk_scores` all created. The failure was a **port conflict** — port 8005 was already in use by PID 24164 from a previous test run.

**Error message:**
```
[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8005): only one usage of each socket address is normally permitted
```

**Resolution:** Killed leftover process with `Stop-Process -Id 24164`. No code changes needed.

**Verdict:** ✅ Not a code bug — port conflict only.

---

### Engine 6 — Vector Database (Port 8006)

**Investigation:**
```powershell
Start-Process python -ArgumentList "-m","uvicorn","vector-database.main:app","--port","18006" `
  -NoNewWindow -RedirectStandardError "data\err_e6.txt"
```

**Finding:** Engine started **successfully** on alternate port 18006. Loaded 0 vectors into in-memory index (expected for fresh DB). Tables created: `vector_records`.

**Stderr output (last lines):**
```
Loaded 0 vectors into in-memory index
Application startup complete.
Uvicorn running on http://127.0.0.1:18006
```

**Resolution:** No code changes needed. Original failure was a port conflict.

**Verdict:** ✅ Not a code bug — port conflict only.

---

### Engine 11 — Policy Fetching (Port 8011)

**Investigation:**
```powershell
Start-Process python -ArgumentList "-m","uvicorn","policy-fetching-engine.main:app","--port","18011" `
  -NoNewWindow -RedirectStandardError "data\err_e11.txt"
```

**Finding:** **REAL BUG.** Crash traceback:
```
File "D:\AIForBharat\AIforBharat\policy-fetching-engine\main.py", line 37, in <module>
    POLICY_STORE_DIR = Path(settings.LOCAL_DATA_DIR) / "policies"
                            ^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'Settings' object has no attribute 'LOCAL_DATA_DIR'
```

**Root Cause:** Line 37 of `policy-fetching-engine/main.py` references `settings.LOCAL_DATA_DIR`, but the `Settings` class in `shared/config.py` did **not** define a `LOCAL_DATA_DIR` field.

**Code at fault (policy-fetching-engine/main.py:37):**
```python
POLICY_STORE_DIR = Path(settings.LOCAL_DATA_DIR) / "policies"
```

**Resolution:** Added `LOCAL_DATA_DIR` field to `shared/config.py`:
```python
# ── Local Data Paths ──────────────────────────────────────────────────
LOCAL_DATA_DIR: str = str(DATA_DIR)
```
This sets `LOCAL_DATA_DIR` to the existing `DATA_DIR` constant (`<project_root>/data/`).

**Post-fix test:** Engine started successfully. Seeded 10 pre-loaded schemes. Tables created: `fetched_documents`, `source_configs`.

**Verdict:** 🐛 Code bug — fixed.

---

### Engine 13 — Analytics Warehouse (Port 8013)

**Investigation:**
```powershell
Start-Process python -ArgumentList "-m","uvicorn","analytics-warehouse.main:app","--port","18013" `
  -NoNewWindow -RedirectStandardError "data\err_e13.txt"
```

**Finding:** Engine started **successfully** on alternate port. Created tables: `analytics_events`, `metric_snapshots`, `funnel_steps`. Subscribed to all events for analytics.

**Stderr output (last lines):**
```
Subscribed to all events for analytics
Application startup complete.
Uvicorn running on http://127.0.0.1:18013
```

**Resolution:** No code changes needed. Original failure was a port conflict.

**Verdict:** ✅ Not a code bug — port conflict only.

---

### Engine 15 — Eligibility Rules (Port 8015)

**Investigation:**
```powershell
Start-Process python -ArgumentList "-m","uvicorn","eligibility-rules-engine.main:app","--port","18015" `
  -NoNewWindow -RedirectStandardError "data\err_e15.txt"
```

**Finding:** Engine started **successfully**. Created tables: `eligibility_rules`, `eligibility_results`. Seeded built-in scheme rules (PM-KISAN, PMJAY, PMAY, etc.).

**Resolution:** No code changes needed. Original failure was a port conflict.

**Verdict:** ✅ Not a code bug — port conflict only.

---

### Engine 16 — Deadline Monitoring (Port 8016)

**Investigation:**
```powershell
Start-Process python -ArgumentList "-m","uvicorn","deadline-monitoring-engine.main:app","--port","18016" `
  -NoNewWindow -RedirectStandardError "data\err_e16.txt"
```

**Finding:** Engine started **successfully**. Created tables: `scheme_deadlines`, `user_deadline_alerts`. Seeded deadline data.

**Resolution:** No code changes needed. Original failure was a port conflict.

**Verdict:** ✅ Not a code bug — port conflict only.

---

### Engine 18 — Government Data Sync (Port 8018)

**Investigation:**
```powershell
Start-Process python -ArgumentList "-m","uvicorn","government-data-sync-engine.main:app","--port","18018" `
  -NoNewWindow -RedirectStandardError "data\err_e18_fix.txt"
```

**Finding:** **REAL BUG.** Same `AttributeError` as Engine 11:
```
AttributeError: 'Settings' object has no attribute 'LOCAL_DATA_DIR'
```

**Code at fault (government-data-sync-engine/main.py:36):**
```python
GOV_DATA_DIR = Path(settings.LOCAL_DATA_DIR) / "gov-data"
```

**Resolution:** Same fix as Engine 11 — `LOCAL_DATA_DIR` added to `shared/config.py`.

**Post-fix test:** Engine started successfully. Seeded government datasets. Tables: `synced_datasets`, `gov_data_records`.

**Verdict:** 🐛 Code bug — fixed (same root cause as Engine 11).

---

### Engine 20 — Speech Interface (Port 8020)

**Investigation:**
```powershell
Start-Process python -ArgumentList "-m","uvicorn","speech-interface-engine.main:app","--port","18020" `
  -NoNewWindow -RedirectStandardError "data\err_e20_fix.txt"
```

**Finding:** **REAL BUG.** Same `AttributeError` as Engines 11 and 18:
```
AttributeError: 'Settings' object has no attribute 'LOCAL_DATA_DIR'
```

**Code at fault (speech-interface-engine/main.py:37):**
```python
AUDIO_DIR = Path(settings.LOCAL_DATA_DIR) / "audio"
```

**Resolution:** Same fix — `LOCAL_DATA_DIR` added to `shared/config.py`.

**Post-fix test:** Engine started successfully. Created table: `voice_sessions`.

**Verdict:** 🐛 Code bug — fixed (same root cause as Engines 11 & 18).

---

## 4. Summary of All Fixes Applied

### Fix 1: Missing `LOCAL_DATA_DIR` in Config (Code Bug)

**File changed:** `shared/config.py`

**What was added** (after line ~102, in the Local Data Paths section):
```python
LOCAL_DATA_DIR: str = str(DATA_DIR)
```

**Impact:** Fixed 3 engines (11, 18, 20) that all referenced `settings.LOCAL_DATA_DIR` at module-level:
| Engine | File | Line | Usage |
|--------|------|------|-------|
| 11 — Policy Fetching | `policy-fetching-engine/main.py` | 37 | `POLICY_STORE_DIR = Path(settings.LOCAL_DATA_DIR) / "policies"` |
| 18 — Gov Data Sync | `government-data-sync-engine/main.py` | 36 | `GOV_DATA_DIR = Path(settings.LOCAL_DATA_DIR) / "gov-data"` |
| 20 — Speech Interface | `speech-interface-engine/main.py` | 37 | `AUDIO_DIR = Path(settings.LOCAL_DATA_DIR) / "audio"` |

### Fix 2: README Schema Documentation (Doc Bug)

Three README files and the master walkthrough had incorrect field names in their request model documentation, causing users to send wrong payloads and get 422 errors.

**Files changed:**

| File | What Changed |
|------|-------------|
| `raw-data-store/README.md` | `RawEventInput` fields: `source` → `source_engine`, `data` → `payload`. `IntegrityVerifyRequest` fields corrected to `event_ids` (list). |
| `neural-network-engine/README.md` | `IntentRequest` fields: `text, language` → `message (required), user_id (optional)` |
| `simulation-engine/README.md` | `SimulateRequest` fields: `base_profile, modified_profile` → `user_id, current_profile, changes, scenario_type`. `LifeEventRequest` also corrected. |
| `walkthrough.md` | What-if simulation example payload updated to use `current_profile` + `changes` instead of `base_profile` + `modified_profile`. |

### Fix 3: Port Conflicts (Not Code Bugs)

5 engines (5, 6, 13, 15, 16) had no code bugs. Their "failures" were caused by leftover Python processes from previous test runs holding the ports. Resolved by killing zombie processes:
```powershell
Get-Process python | Stop-Process -Force
```

---

## 5. Correct Request Payloads (Reference)

### POST `/raw-data/events` (Engine 3, Port 8003)
```json
{
  "event_type": "user.login",
  "source_engine": "login_register_engine",
  "user_id": "usr_abc123",
  "payload": {"ip": "192.168.1.1", "method": "password"}
}
```
- `event_type` — **required** (str)
- `source_engine` — **required** (str)
- `user_id` — optional (str, default null)
- `payload` — optional (dict, default `{}`)

### POST `/ai/intent` (Engine 7, Port 8007)
```json
{
  "message": "मुझे PM-KISAN योजना के बारे में बताइए",
  "user_id": "usr_abc123"
}
```
- `message` — **required** (str)
- `user_id` — optional (str, default null)

### POST `/simulate/what-if` (Engine 17, Port 8017)
```json
{
  "user_id": "usr_abc123",
  "current_profile": {
    "age": 28,
    "annual_income": 400000,
    "occupation": "salaried",
    "state": "Uttar Pradesh",
    "category": "general"
  },
  "changes": {
    "annual_income": 180000,
    "occupation": "farmer"
  },
  "scenario_type": "custom"
}
```
- `user_id` — **required** (str)
- `current_profile` — **required** (dict)
- `changes` — **required** (dict)
- `scenario_type` — optional (str, default `"custom"`)

### POST `/raw-data/integrity/verify` (Engine 3, Port 8003)
```json
{
  "event_ids": ["evt_abc123", "evt_def456"]
}
```
- `event_ids` — optional (list of str, default `[]`)

### POST `/identity/create` (Engine 2, Port 8002)
```json
{
  "user_id": "usr_abc123",
  "name": "Amandeep Singh",
  "phone": "9876543210",
  "email": "aman@example.com",
  "aadhaar": "123456789012"
}
```
- `user_id` — **required** (str)
- All other fields — optional (str, default null)

---

## 6. Final End-to-End Test Results (After All Fixes)

**Test command:**
```powershell
$ports = @(8000,8001,8002,8003,8004,8005,8006,8007,8008,8010,8011,8012,8013,8014,8015,8016,8017,8018,8019,8020,8021)
foreach($p in $ports) {
  try {
    $r = Invoke-WebRequest -Uri "http://localhost:$p/health" -TimeoutSec 3
    Write-Host "$p : OK"
  } catch {
    Write-Host "$p : FAIL"
  }
}
```

**Final output — 21/21 PASS:**
```
8000 : OK    ← API Gateway
8001 : OK    ← Login Register
8002 : OK    ← Identity Engine
8003 : OK    ← Raw Data Store
8004 : OK    ← Metadata Engine
8005 : OK    ← Processed Metadata Store
8006 : OK    ← Vector Database
8007 : OK    ← Neural Network
8008 : OK    ← Anomaly Detection
8010 : OK    ← Chunks Engine
8011 : OK    ← Policy Fetching
8012 : OK    ← JSON User Info
8013 : OK    ← Analytics Warehouse
8014 : OK    ← Dashboard Interface
8015 : OK    ← Eligibility Rules
8016 : OK    ← Deadline Monitoring
8017 : OK    ← Simulation Engine
8018 : OK    ← Gov Data Sync
8019 : OK    ← Trust Scoring
8020 : OK    ← Speech Interface
8021 : OK    ← Doc Understanding
```

---

## 7. Successful Endpoint Tests Confirmed

These endpoints were verified to return 200 OK with correct response bodies during testing:

| Method | Endpoint | Port | Response |
|--------|----------|------|----------|
| GET | `/health` | ALL 21 | `{"status": "healthy", ...}` |
| GET | `/raw-data/events` | 8003 | 200 OK — list of events |
| POST | `/metadata/process` | 8004 | 200 OK — derived attributes computed |
| POST | `/anomaly/check` | 8008 | 200 OK — anomaly score returned |
| GET | `/` | 8010 | 200 OK — service directory |

---

## 8. Database Tables Created Successfully

All SQLAlchemy models auto-created their tables in `data/aiforbharat.db` on first startup:

| Engine | Tables |
|--------|--------|
| Login Register | `users` |
| Identity | `identity_records` |
| Raw Data Store | `raw_events` |
| Metadata | `metadata_records` |
| Processed Metadata | `user_metadata`, `user_derived_attributes`, `user_eligibility_cache`, `user_risk_scores` |
| Vector Database | `vector_records` |
| Neural Network | `conversation_logs` |
| Anomaly Detection | `anomaly_records` |
| Chunks Engine | `document_chunks` |
| Policy Fetching | `fetched_documents`, `source_configs` |
| JSON User Info | `user_profiles` |
| Analytics Warehouse | `analytics_events`, `metric_snapshots`, `funnel_steps` |
| Eligibility Rules | `eligibility_rules`, `eligibility_results` |
| Deadline Monitoring | `scheme_deadlines`, `user_deadline_alerts` |
| Simulation | `simulation_results` |
| Gov Data Sync | `synced_datasets`, `gov_data_records` |
| Trust Scoring | `trust_scores` |
| Speech Interface | `voice_sessions` |
| Doc Understanding | `processed_documents` |

---

## 9. How to Run All Engines (Reference)

### Start all 21 engines:
```powershell
cd d:\AIForBharat\AIforBharat

$engines = @(
  "api-gateway:8000", "login-register-engine:8001", "identity-engine:8002",
  "raw-data-store:8003", "metadata-engine:8004", "processed-user-metadata-store:8005",
  "vector-database:8006", "neural-network-engine:8007", "anomaly-detection-engine:8008",
  "chunks-engine:8010", "policy-fetching-engine:8011", "json-user-info-generator:8012",
  "analytics-warehouse:8013", "dashboard-interface:8014", "eligibility-rules-engine:8015",
  "deadline-monitoring-engine:8016", "simulation-engine:8017", "government-data-sync-engine:8018",
  "trust-scoring-engine:8019", "speech-interface-engine:8020", "document-understanding-engine:8021"
)

foreach ($e in $engines) {
  $parts = $e -split ":"
  Start-Process python -ArgumentList "-m","uvicorn","$($parts[0]).main:app","--port","$($parts[1])" -WindowStyle Hidden
}
```

### Stop all engines:
```powershell
Get-Process python | Stop-Process -Force
```

### Health check all engines:
```powershell
@(8000,8001,8002,8003,8004,8005,8006,8007,8008,8010,8011,8012,8013,8014,8015,8016,8017,8018,8019,8020,8021) |
  ForEach-Object { try { Invoke-WebRequest "http://localhost:$_/health" -TimeoutSec 3 | Out-Null; "$_ : OK" } catch { "$_ : FAIL" } }
```

---

## 10. Conclusion

| Metric | Value |
|--------|-------|
| Total engines tested | 21 |
| Engines with code bugs | 3 (Engines 11, 18, 20) |
| Engines with port conflicts only | 5 (Engines 5, 6, 13, 15, 16) |
| Documentation fixes | 4 files (3 READMEs + walkthrough.md) |
| Code files changed | 1 (`shared/config.py`) |
| Final pass rate | **21/21 (100%)** |
| Root cause | Single missing config field: `LOCAL_DATA_DIR` |
