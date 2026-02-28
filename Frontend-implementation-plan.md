# AGENTIC CODER BLUEPRINT: AIforBharat Frontend

**Objective:** Build a premium, local-first React/Next.js frontend for 21 backend engines.
**Local API Gateway:** `http://localhost:8000/api/v1`
**Constraints:** NO AWS, NO DigiLocker, NO External Notifications. Local-first only.

---

## 1. Project Initialization Strict Commands

Run these commands in sequence to scaffold the environment:

```bash
# 1. Initialize Next.js with strict defaults
npx create-next-app@latest aiforbharat-ui --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes

# 2. Install Primary UI & Layout Libraries
npm i @nextui-org/react framer-motion lucide-react lenis clsx tailwind-merge

# 3. Install AI & Assistant Stack
npm i @copilotkit/react-core @copilotkit/react-ui @assistant-ui/react @gravity-ui/uikit @gravity-ui/icons assistant-ui-kit copilot-kit-react-sdk

# 4. Install Data, Charting & Workflow Libraries
npm i reactflow recharts mapcn @tanstack/react-query zustand axios

# 5. Initialize ShadCN UI (Automated)
npx shadcn-ui@latest init --yes
# Install specific ShadCN components needed
npx shadcn-ui@latest add button card dialog dropdown-menu form input label scroll-area select separator sidebar switch table tabs toast tooltip
```

---

## 2. Exact Folder Structure

```text
src/
├── app/
│   ├── (auth)/
│   │   └── login/page.tsx           # E1: Auth UI
│   ├── (dashboard)/
│   │   ├── layout.tsx               # Global Sidebar & Smooth Scroll
│   │   ├── page.tsx                 # E14: Home Widgets
│   │   ├── eligibility/page.tsx      # E15: Rules Result
│   │   ├── simulator/page.tsx        # E17: What-If UI
│   │   ├── chat/page.tsx            # E7/E20: AI Assistant
│   │   └── profile/page.tsx         # E2/E4/E12: Identity Vault
│   ├── layout.tsx                   # Providers (NextUI, QueryClient, Lenis)
│   └── globals.css                  # UIverse/CSS Button injects
├── components/
│   ├── ui/                          # ShadCN Base
│   ├── chat/
│   │   ├── AssistantOverlay.tsx     # assistant-ui implementation
│   │   └── PromptBar.tsx            # Prompt Kit / AIKit
│   ├── dashboard/
│   │   ├── EngineStatusMap.tsx      # React Flow Diagram
│   │   ├── StatCard.tsx             # Hero UI (NextUI) Cards
│   │   └── EligibilityWidget.tsx    # Custom UIverse style
│   ├── shared/
│   │   ├── Sidebar.tsx              # ShadCN Sidebar
│   │   └── SmoothScrollProvider.tsx # Lenis implementation
│   └── viz/
│       ├── TrustMetric.tsx          # Recharts/NextUI
│       └── DistrictMap.tsx          # mapcn
├── lib/
│   ├── api-client.ts                # Axios instance for port 8000
│   ├── store.ts                     # Zustand Global State
│   └── utils.ts                     # ShadCN cn() helper
└── types/
    └── api.d.ts                     # Generated from frontend-endpoints
```

---

## 3. Phased Execution Checklists

### Phase 1: Environment & Layout (Foundation)
- [ ] Implement `SmoothScrollProvider` using `lenis`.
- [ ] Setup `src/lib/api-client.ts` pointing to `http://localhost:8000/api/v1`.
- [ ] Build global `Sidebar` and `Navbar` using `ShadCN`.
- [ ] **Acceptance:** App scrolls smoothly; Sidebar is responsive; `/health` endpoint reachable via `api-client`.

### Phase 2: Authentication & Identity (E0 Orchestrator, E1, E2, E3, E4)
- [ ] Create `/login` page with `ShadCN` forms + `UIverse` hover effects.
- [ ] Implement `/api/v1/onboard` (Orchestrator route) for unified registration, tracking to Identity Vault.
- [ ] Implement `/api/v1/auth/login` logic and store JWT in `localStorage`.
- [ ] Build `/profile` page using `Hero UI (NextUI)` cards for encrypted vault data (E3).
- [ ] **Acceptance:** User can onboard and log in; JWT persists; Identity vault data displays decrypted fields.

### Phase 3: AI Chat & RAG Workspace (E0 Orchestrator, E6, E7, E10, E21)
- [ ] Build `/chat` interface in `src/components/chat/AssistantOverlay.tsx` using **assistant-ui**.
- [ ] Integrate **CopilotKit** for document-aware Q&A sidebars.
- [ ] Implement Orchestrator composite routes: `/api/v1/query` (RAG) and `/api/v1/voice-query` (Voice).
- [ ] **Acceptance:** Assistant routes to E7 through API Gateway orchestrator; returns Llama 3.1 responses; Intent classification icons appear in chat bubbles.

### Phase 4: Eligibility & Simulation (E0 Orchestrator, E15, E17)
- [ ] Create `/eligibility` page using `ShadCN` tables + `NextUI` Accordions.
- [ ] Route eligibility checks through the composite `/api/v1/check-eligibility` orchestrator endpoint.
- [ ] Implement `/simulator` via the `/api/v1/simulate` composite route, with `ShadCN` sliders and `Recharts` for "What-If" visualization.
- [ ] **Acceptance:** Eligibility verdicts color-coded with LLM explanations; Sliders trigger re-computation of simulation results with impact deltas.

### Phase 5: Dashboard Analytics & Orchestration (E14, E13, E19)
- [ ] Build `/dashboard` home with 8 feature widgets using **UIverse** custom CSS.
- [ ] Implement `EngineStatusMap.tsx` using **React Flow** to map the 21-engine data flow.
- [ ] Connect `TrustMetric.tsx` to `/api/v1/trust/compute`.
- [ ] **Acceptance:** All 8 widgets display dynamic counts; React Flow map shows green/red status for local ports.

---

## 4. Component-to-Library Hard Mapping

| Component File | Required Library | Styling Target |
|----------------|------------------|----------------|
| `AssistantOverlay.tsx` | `assistant-ui` | Premium chat experience |
| `StatCard.tsx` | `Hero UI (NextUI)` | Animated progress/metrics |
| `EngineStatusMap.tsx` | `React Flow` | Backend orchestration map |
| `DistrictMap.tsx` | `mapcn` | NFHS-5 geospatial stats |
| `GlobalSearch.tsx` | `AIKit (Gravity UI)` | Intent-aware command bar |
| `PrimaryButton.tsx` | `CSS Buttons` | Sleek hover/click interactions |
| `Sidebar.tsx` | `ShadCN` | Functional navigation |
| `EligibilityWidget.tsx`| `UIverse` | High-impact interactive card |

---

## 5. Local API Integration Rules

1. **Base URL:** Always use `http://localhost:8000/api/v1`.
2. **Authentication:** 
   - Send `Authorization: Bearer <token>` for all endpoints EXCEPT `/auth/login`, `/auth/register`, `/onboard`, and `/voice-query`.
3. **Data Fetching:**
   - Use `Zustand` for user session and theme state.
   - Use `React Query` for engine data (caching: 5 mins, stale: 1 min).
4. **Local constraints:**
   - No `s3://` URLs (all local `/audio/` or `/cache/` paths).
   - No SMS/Email (log OTP to console as per Backend E1 logic).
   - Identity verification is stubbed (always return "Verified" UI status for now).

---
**FINAL GOAL:** Execute all Phase 1-5 steps. Output must be a functional, beautiful, and complete Local Civic OS frontend.
