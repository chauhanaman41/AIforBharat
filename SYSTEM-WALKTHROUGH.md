# AIforBharat — System Walkthrough

> **Version:** 1.0  
> **Date:** February 28, 2026  
> **Status:** Development phase complete — QA signed off (100% PASS)

A step-by-step guide to booting the entire AIforBharat platform on your local machine, interacting with every feature, and understanding what's happening under the hood.

---

## Table of Contents

1. [Prerequisites & Environment](#1-prerequisites--environment)
2. [Boot Sequence (Step-by-Step)](#2-boot-sequence-step-by-step)
3. [The User Journey](#3-the-user-journey-how-to-test-the-ui)
4. [Architecture Notes](#4-architecture-notes-for-future-reference)

---

## 1. Prerequisites & Environment

### Required Software

| Tool | Minimum Version | Check Command | Notes |
|------|----------------|---------------|-------|
| **Node.js** | 18.17+ (LTS recommended: 20.x or 22.x) | `node -v` | Next.js 16 requires Node 18.17+ |
| **npm** | 9+ (ships with Node) | `npm -v` | Used for frontend dependency management |
| **Python** | 3.11+ | `python --version` | Required for all 21 backend engines |
| **pip** | 23+ | `pip --version` | Python package manager |
| **Git** | 2.x | `git --version` | For cloning the repository |

### Hardware Recommendations

- **RAM:** 8 GB minimum (16 GB recommended — 21 Python processes + Next.js dev server)
- **CPU:** 4+ cores (engines run concurrently)
- **Disk:** ~2 GB free (node_modules + Python packages + SQLite databases)
- **OS:** Windows 10/11, macOS, or Linux

### Ports Used

The system occupies **22 ports**. Ensure none of them are in use:

| Port | Service |
|------|---------|
| **3000** | Next.js Frontend (dev server) |
| **8000** | API Gateway / Orchestrator (E0) |
| **8001** | Login & Register Engine (E1) |
| **8002** | Identity Engine (E2) |
| **8003** | Raw Data Store (E3) |
| **8004** | Metadata Engine (E4) |
| **8005** | Processed User Metadata Store (E5) |
| **8006** | Vector Database (E6) |
| **8007** | Neural Network Engine (E7) |
| **8008** | Anomaly Detection Engine (E8) |
| **8010** | Chunks Engine (E9) |
| **8011** | Policy Fetching Engine (E10/E11) |
| **8012** | JSON User Info Generator (E12) |
| **8013** | Analytics Warehouse (E13) |
| **8014** | Dashboard Interface / BFF (E14) |
| **8015** | Eligibility Rules Engine (E15) |
| **8016** | Deadline Monitoring Engine (E16) |
| **8017** | Simulation Engine (E17) |
| **8018** | Government Data Sync Engine (E18) |
| **8019** | Trust Scoring Engine (E19) |
| **8020** | Speech Interface Engine (E20) |
| **8021** | Document Understanding Engine (E21) |

> Port 8009 is intentionally unused.

---

## 2. Boot Sequence (Step-by-Step)

### Step 2.1 — Install Python Dependencies

Open a terminal at the **project root** (`AIforBharat/`):

```bash
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic pydantic-settings
pip install python-jose[cryptography] passlib[bcrypt] bcrypt
pip install openai httpx python-multipart cryptography
```

> These cover FastAPI (async web framework), SQLAlchemy 2.0 (async ORM), SQLite via aiosqlite, JWT auth, bcrypt hashing, AES-256-GCM encryption, NVIDIA NIM integration, and HTTP client for inter-engine communication.

### Step 2.2 — Install Frontend Dependencies

Open a **second terminal** and navigate to the frontend folder:

```bash
cd aiforbharat-ui
npm install
```

This installs ~40+ packages including Next.js 16, React 19, Tailwind v4, ShadCN UI, Hero UI, React Flow, Recharts, Framer Motion, Zustand, React Query, CopilotKit, assistant-ui, and more.

### Step 2.3 — Start All 21 Backend Engines

Go back to the **first terminal** at the project root (`AIforBharat/`). You need to start each engine as a separate process. The fastest way is to open multiple terminal tabs/panes or run them in the background.

**Option A — Manual (one terminal per engine):**

Open 21 separate terminals at the project root and run one command per terminal:

```bash
# ─── Core Gateway (START THIS FIRST) ─────────────────────────────────
uvicorn api-gateway.main:app --port 8000 --reload

# ─── User Engines ─────────────────────────────────────────────────────
uvicorn login-register-engine.main:app --port 8001 --reload
uvicorn identity-engine.main:app --port 8002 --reload
uvicorn json-user-info-generator.main:app --port 8012 --reload

# ─── Data Engines ─────────────────────────────────────────────────────
uvicorn raw-data-store.main:app --port 8003 --reload
uvicorn metadata-engine.main:app --port 8004 --reload
uvicorn processed-user-metadata-store.main:app --port 8005 --reload
uvicorn vector-database.main:app --port 8006 --reload

# ─── AI Engines ───────────────────────────────────────────────────────
uvicorn neural-network-engine.main:app --port 8007 --reload
uvicorn anomaly-detection-engine.main:app --port 8008 --reload
uvicorn chunks-engine.main:app --port 8010 --reload
uvicorn speech-interface-engine.main:app --port 8020 --reload
uvicorn document-understanding-engine.main:app --port 8021 --reload

# ─── System Engines ───────────────────────────────────────────────────
uvicorn policy-fetching-engine.main:app --port 8011 --reload
uvicorn analytics-warehouse.main:app --port 8013 --reload
uvicorn dashboard-interface.main:app --port 8014 --reload
uvicorn eligibility-rules-engine.main:app --port 8015 --reload
uvicorn deadline-monitoring-engine.main:app --port 8016 --reload
uvicorn simulation-engine.main:app --port 8017 --reload
uvicorn government-data-sync-engine.main:app --port 8018 --reload
uvicorn trust-scoring-engine.main:app --port 8019 --reload
```

**Option B — PowerShell Background Jobs (Windows, single terminal):**

```powershell
# Run from the project root (AIforBharat/)
$engines = @(
  @{Name="api-gateway";                   Port=8000},
  @{Name="login-register-engine";         Port=8001},
  @{Name="identity-engine";               Port=8002},
  @{Name="raw-data-store";                Port=8003},
  @{Name="metadata-engine";               Port=8004},
  @{Name="processed-user-metadata-store"; Port=8005},
  @{Name="vector-database";               Port=8006},
  @{Name="neural-network-engine";         Port=8007},
  @{Name="anomaly-detection-engine";      Port=8008},
  @{Name="chunks-engine";                 Port=8010},
  @{Name="policy-fetching-engine";        Port=8011},
  @{Name="json-user-info-generator";      Port=8012},
  @{Name="analytics-warehouse";           Port=8013},
  @{Name="dashboard-interface";           Port=8014},
  @{Name="eligibility-rules-engine";      Port=8015},
  @{Name="deadline-monitoring-engine";    Port=8016},
  @{Name="simulation-engine";            Port=8017},
  @{Name="government-data-sync-engine";  Port=8018},
  @{Name="trust-scoring-engine";         Port=8019},
  @{Name="speech-interface-engine";      Port=8020},
  @{Name="document-understanding-engine";Port=8021}
)

foreach ($e in $engines) {
  Start-Job -Name $e.Name -ScriptBlock {
    param($n, $p)
    Set-Location $using:PWD
    uvicorn "$n.main:app" --port $p
  } -ArgumentList $e.Name, $e.Port
}

# Check all jobs are running:
Get-Job | Format-Table Name, State
```

**Option C — Bash Background (macOS / Linux, single terminal):**

```bash
#!/bin/bash
# Save as start_all.sh and run: chmod +x start_all.sh && ./start_all.sh

engines=(
  "api-gateway:8000"
  "login-register-engine:8001"
  "identity-engine:8002"
  "raw-data-store:8003"
  "metadata-engine:8004"
  "processed-user-metadata-store:8005"
  "vector-database:8006"
  "neural-network-engine:8007"
  "anomaly-detection-engine:8008"
  "chunks-engine:8010"
  "policy-fetching-engine:8011"
  "json-user-info-generator:8012"
  "analytics-warehouse:8013"
  "dashboard-interface:8014"
  "eligibility-rules-engine:8015"
  "deadline-monitoring-engine:8016"
  "simulation-engine:8017"
  "government-data-sync-engine:8018"
  "trust-scoring-engine:8019"
  "speech-interface-engine:8020"
  "document-understanding-engine:8021"
)

for entry in "${engines[@]}"; do
  IFS=":" read -r name port <<< "$entry"
  echo "Starting $name on port $port..."
  uvicorn "$name.main:app" --port "$port" &
done

echo "All engines launched. Press Ctrl+C to stop all."
wait
```

### Step 2.4 — Verify Backend Health

Wait about 10 seconds for all engines to initialize, then verify:

```bash
# Quick health check on the API Gateway
curl http://localhost:8000/health

# Full engine health probe (hits all 21 engines)
curl http://localhost:8000/api/v1/engines/health
```

You should see a JSON response listing all engines with `"status": "healthy"`. If any engine shows `"unreachable"`, check that its terminal/process is running.

Alternatively, run the provided test script:

```bash
python test_all_engines.py
```

### Step 2.5 — Start the Next.js Frontend

In the **frontend terminal** (inside `aiforbharat-ui/`):

```bash
npm run dev
```

Wait for the output:

```
  ▲ Next.js 16.1.6
  - Local:   http://localhost:3000
  - Ready in ~3s
```

### Step 2.6 — Open the App

Open your browser and navigate to:

```
http://localhost:3000
```

You'll be redirected to the **Login page** (`/login`) since you're not authenticated. The system is ready!

---

## 3. The User Journey (How to Test the UI)

### Step 3.1 — Registration (First-Time User)

Since there are no pre-seeded users, you need to register first.

1. On the login page, click the **"Create an account"** link at the bottom.
2. You'll arrive at `/register`. Fill in the form:

   | Field | Example Value |
   |-------|---------------|
   | **Full Name** | `Raj Kumar` |
   | **Phone** | `9851561470` |
   | **Password** | `SecurePassword123!` |
   | **Confirm Password** | `SecurePassword123!` |
   | **State** | `Uttar Pradesh` |
   | **Annual Income** | `120000` |
   | **Consent** | ✅ Check the box |

3. Click the **"Register & Begin"** button (the UIverse-style glowing button).
4. The orchestrator fires a composite onboarding flow: **E1** (register) → **E2** (identity) → **E4** (metadata) → **E5** (processed metadata) → **E15** (eligibility) → **E12** (user info).
5. On success, you're automatically logged in and redirected to the **Dashboard** (`/`).

> **Remember your phone number and password** — you'll use these to log in next time.

### Step 3.2 — The Dashboard (Phase 5)

After login, you land on the main dashboard. Here's what you should see:

- **Top row:** A personalised greeting ("Welcome back, Raj") plus a compact Trust Score gauge.
- **8 StatCard widgets** in a responsive grid — showing live metrics like total events, active users, engine count, uptime percentage, trust score, active schemes, documents processed, and active sessions. Each card has animated progress bars and trend indicators.
- **Engine Orchestration Map** — A large React Flow interactive canvas showing all 21 backend engines as draggable nodes with animated connection lines. Each node shows a green (healthy) or red (unreachable) status dot that pulses in real time.
  - **Try it:** Drag nodes around. Use the scroll wheel to zoom. Click the minimap in the bottom-right corner.
- **Bottom section (3 columns):**
  - Trust Score gauge with component breakdown
  - Recent Activity feed (last 8 backend events)
  - Event distribution sparkline chart

### Step 3.3 — Analytics Page (Phase 5)

Click **"Analytics"** in the sidebar (second item, BarChart icon). You'll see four tabs:

| Tab | What It Shows |
|-----|---------------|
| **Overview** | 4 stat cards + event distribution bar chart + engine call share pie chart + scheme popularity area chart + events table |
| **Geospatial** | Full-screen India choropleth map. Use the dropdown to switch metrics (Active Schemes, Beneficiaries, Literacy Rate, Trust Score, Population). Hover over states to see tooltip details. Use zoom buttons to navigate. |
| **Engines** | The full React Flow engine map + a filterable health table (filter by All / Healthy / Unreachable). |
| **Trust** | Full trust score radial gauge + component weights explanation card listing the 5 trust dimensions and their weights. |

### Step 3.4 — AI Chat (Phase 3)

Click **"AI Chat"** in the sidebar (fourth item, MessageSquare icon). This opens the full-screen chat interface.

**Test the AI by typing these messages:**

| What to Type | What Happens |
|-------------|--------------|
| `Am I eligible for PM-KISAN if I own 3 acres of land?` | Triggers the RAG pipeline (E0 → E7 → E6 → E19). You'll see the assistant stream a response with cited sources. |
| `Tell me about Ayushman Bharat` | Scheme information query — routes through vector search + neural network. |
| `Translate this to Hindi: I am eligible for five schemes` | Tests the translation pipeline (E7). You'll see the response in Devanagari script. |

**Things to observe:**
- The **intent badge** appears below each assistant message (e.g., `scheme_query`, `eligibility`, `translation`) with a shimmer animation.
- The **typing indicator** (three bouncing dots) appears while the AI processes.
- If the backend is slow (>3 seconds), you'll see a **"Connecting to Edge Fallback..."** toast notification — this is the graceful timeout handling.

**CopilotKit Floating Widget:**
- Press **`Ctrl+K`** on any page to toggle the floating AI assistant widget (bottom-right corner, green glow pulse).
- You can type quick questions here without leaving the current page.

**NLP Toolbar:**
- Inside the chat page, look for the **NLP Tools** section with three cards: **Translate**, **Summarize**, and **Classify**.
- Click **Summarize** → paste any long text → click submit. The E7 Neural Network will generate a summary.

### Step 3.5 — Eligibility Check (Phase 4)

Click **"Eligibility"** in the sidebar (third item, Shield icon).

1. You'll see a form with pre-populated profile fields (from your registration data). You can adjust:
   - **Age:** `44`
   - **Annual Income:** `120000`
   - **State:** `UP`
   - **Category:** `general`
2. Click the **"Check My Eligibility"** button (UIverse glow-bordered button).
3. Watch the results appear:
   - **Green chips** = schemes you're eligible for
   - **Amber chips** = partial eligibility
   - **Red chips** = not eligible
   - Each result card has a **Sparkles** icon with an AI-generated explanation.
   - A summary toast appears: "You're eligible for X out of Y schemes checked."

### Step 3.6 — What-If Simulator (Phase 4)

Click **"Simulator"** in the sidebar (fourth item, FlaskConical icon).

1. **Current Profile** is auto-filled from your user data.
2. Under **"What If..."**, change a value. For example:
   - Change **Annual Income** from `120000` → `400000`
3. Click **"Run Simulation"**.
4. Watch the results:
   - **Recharts BarChart** animates showing Before vs After comparison.
   - **Two-column grid** appears: "Schemes Gained" (green border) and "Schemes Lost" (red border).
   - Each scheme card uses the **UIverse glow effect** (spinning conic gradient border).
   - A summary chip shows the **Net Impact** (positive / negative / neutral).

### Step 3.7 — Profile Page

Click **"Profile"** in the sidebar (User icon). You'll see:

- Your encrypted identity vault (Hero UI cards with masked fields).
- Document verification status (mocked locally as "Verified" chips).
- Account settings.

### Step 3.8 — Engine Status Page

Click **"Engine Status"** in the sidebar (Activity icon). This shows a dedicated engine monitoring view.

### Step 3.9 — Testing Graceful Error Handling

To see the frontend's error resilience in action:

**Test 1 — Simulate a backend timeout:**
1. Stop one of the backend engine terminals (e.g., kill the Neural Network Engine on port 8007 with `Ctrl+C`).
2. Go to the **AI Chat** and type a message.
3. After ~3 seconds you'll see the **"Connecting to Edge Fallback..."** toast.
4. After ~15 seconds the chat will display: *"Sorry, I'm having trouble connecting to the AI service."*
5. The Engine Status Map on the dashboard will show that engine's node turning **red** on the next poll cycle (30 seconds).

**Test 2 — Simulate a 404 (Policy Ingestion):**
1. If any API call results in a 404, you'll see a **ShadCN Toast notification** saying "Resource Not Found" with the specific endpoint.
2. For policy-related 404s, the toast reads: *"External URL scraping is disabled in local mode. Utilizing mock policies instead."*

**Test 3 — Simulate all engines down:**
1. Stop the API Gateway (port 8000).
2. Every page will show graceful loading states (shimmer skeletons) and Sonner toast errors.
3. The app will **not crash** — React Query retries and error boundaries contain failures.

> **To restore:** Simply restart the stopped engine(s) with their `uvicorn` command. The frontend will auto-recover on the next polling cycle.

---

## 4. Architecture Notes (For Future Reference)

### Local-First Architecture

The entire AIforBharat platform runs **100% locally** on your machine. There are:

- **NO AWS services** — No S3, Lambda, API Gateway, Cognito, SNS, or SQS.
- **NO Digilocker integration** — Identity verification is mocked locally via E2 (Identity Engine) returning "Verified" status for development.
- **NO external notification systems** — OTP codes are logged to the engine's terminal output (stdout), not sent via SMS/email. Check the Login/Register Engine terminal to see OTPs.
- **NO external database** — All data is stored in SQLite databases (WAL mode) in local `.db` files within each engine's directory.
- **NO cloud AI** — NVIDIA NIM models (Llama 3.1 70B/8B) are called via the OpenAI SDK format, but gracefully degrade to local fallbacks when unavailable.

### Why These Bypasses Exist

This is a **development phase** build. The architectural pattern is designed so that:

1. **AWS** can be plugged in later (S3 for file storage, Cognito for auth, etc.) by swapping config values in `shared/config.py`.
2. **Digilocker** verification can replace the mock identity engine response when official API access is granted.
3. **Notification services** (SMS/email) can be connected by implementing the actual providers behind the existing event bus subscribers.

The frontend already handles all these graceful degradation paths — when a backend engine is unavailable or returns errors, Sonner toasts, error boundaries, and fallback UI states activate automatically.

### Technology Stack Summary

**Frontend (Port 3000):**

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 16.1.6 (App Router) |
| UI Runtime | React 19.2.3 |
| Styling | Tailwind CSS v4 |
| Component Libraries | ShadCN UI (19+ components) + Hero UI / NextUI + UIverse CSS Buttons |
| State Management | Zustand 5 (persist) + React Query 5 (server state) |
| Data Visualization | Recharts 3.7, React Flow 11, react-simple-maps 3 |
| Animation | Framer Motion 12 |
| AI Chat | CopilotKit + assistant-ui + Prompt Kit |
| HTTP Client | Axios (interceptors for JWT auto-refresh, 404/timeout toasts) |
| Forms | React Hook Form + Zod v4 |
| Language | TypeScript 5 (strict, 0 errors) |

**Backend (Ports 8000–8021):**

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (async) |
| Database | SQLite + aiosqlite (WAL mode) |
| Auth | JWT (HS256, 30 min access / 7 day refresh) + bcrypt (12 rounds) |
| Encryption | AES-256-GCM (PII fields) |
| AI/LLM | NVIDIA NIM (OpenAI SDK wrapper) |
| Inter-Engine | httpx (async HTTP) with circuit breakers |
| Event System | In-memory pub/sub event bus |
| Language | Python 3.11+ |

### Data Flow Overview

```
Browser (localhost:3000)
    │
    │  Axios (JWT Bearer)
    ▼
API Gateway (localhost:8000)
    │
    ├──→ Auth (E1, E2)          Registration, Login, Identity
    ├──→ Data Pipeline (E3–E6)  Storage, Metadata, Vectors
    ├──→ AI Pipeline (E7–E9)    Neural Net, Anomaly, Chunks
    ├──→ System (E10–E14)       Policies, Analytics, Dashboard
    ├──→ Rules (E15–E18)        Eligibility, Deadlines, Simulation
    └──→ Trust & Voice (E19–E21) Scoring, Speech, Documents
```

Every composite route goes through the **Orchestrator** inside the API Gateway, which chains engine calls sequentially with circuit breakers (5 failures → open, 30s recovery). All operations end with an audit POST to the Raw Data Store (E3).

### Files That Matter

| File | Purpose |
|------|---------|
| `shared/config.py` | All engine URLs, ports, feature flags, crypto keys |
| `api-gateway/orchestrator.py` | Composite routing + circuit breakers |
| `api-gateway/routes.py` | API endpoint definitions |
| `aiforbharat-ui/src/lib/api-client.ts` | Axios instance (15s timeout, JWT interceptor, 404/timeout toasts) |
| `aiforbharat-ui/src/lib/store.ts` | Zustand global state (user, auth, preferences) |
| `aiforbharat-ui/src/hooks/` | All React Query hooks (auth, chat, eligibility, analytics) |

---

## Quick-Start Cheat Sheet

```bash
# ── Terminal 1: Python deps (one-time) ────────────────────────────────
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic pydantic-settings
pip install python-jose[cryptography] passlib[bcrypt] bcrypt
pip install openai httpx python-multipart cryptography

# ── Terminal 1: Start all engines (PowerShell one-liner) ──────────────
cd AIforBharat
# Start gateway first, then all others as background jobs (see §2.3)

# ── Terminal 2: Frontend ──────────────────────────────────────────────
cd aiforbharat-ui
npm install          # one-time
npm run dev          # → http://localhost:3000

# ── Verify ────────────────────────────────────────────────────────────
curl http://localhost:8000/health
# Open browser → http://localhost:3000 → Register → Explore!
```

---

> **You're all set.** Register a user, explore the dashboard, chat with the AI, run eligibility checks, simulate what-if scenarios, and marvel at the 21-engine architecture on the React Flow map. Enjoy! 🚀
