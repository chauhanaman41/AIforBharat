# Dashboard Interface Engine — Design & Plan

## 1. Purpose

The Dashboard Interface Engine is the **personalized civic command center** that renders a citizen's complete civic profile into an interactive, actionable UI. It consumes the assembled profile from the JSON User Info Generator, pre-computed analytics from the Analytics Warehouse, and real-time updates via WebSocket/SSE to present eligibility alerts, application trackers, impact predictions, tax reminders, civic heatmaps, voting notifications, and policy simulation sliders.

This is NOT just a visualization layer — it is an **intelligent presentation engine** that prioritizes information based on urgency, relevance, and user context, powered by personalized ranking from the Neural Network Engine.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Eligibility Alerts** | Prominent cards for newly eligible schemes with one-click apply actions |
| **Application Tracker** | Status pipeline for all active scheme applications (applied → verified → approved → disbursed) |
| **Impact Predictions** | Visual cards showing predicted life events and recommended preparations |
| **Tax Reminders** | Calendar-integrated deadline alerts with countdown timers |
| **Civic Heatmaps** | Interactive maps showing scheme adoption, benefit distribution by region |
| **Voting Notifications** | Election alerts, booth info, candidate data, voting reminders |
| **Policy Simulation Sliders** | "What if?" interactive controls triggering Simulation Engine queries |
| **Profile Completeness Nudges** | Gamified progress bar encouraging users to complete missing profile data |
| **Multilingual Support** | Interface fully translated across 22 scheduled Indian languages |
| **Accessibility** | WCAG 2.1 AA compliant, screen reader support, voice navigation via Riva |
| **Offline Mode** | PWA with cached profile data for low-connectivity regions |
| **Real-Time Updates** | WebSocket/SSE for live dashboard updates without page refresh |

---

## 3. Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Dashboard Interface Engine                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Presentation Layer                      │    │
│  │                                                           │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │    │
│  │  │Eligibility│ │Application│ │ Deadline │ │  Impact    │  │    │
│  │  │ Alert    │ │ Tracker  │ │ Calendar │ │ Prediction │  │    │
│  │  │ Cards    │ │ Pipeline │ │          │ │ Cards      │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │    │
│  │                                                           │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │    │
│  │  │  Civic   │ │ Voting   │ │ Policy   │ │  Profile   │  │    │
│  │  │ Heatmap  │ │ Center   │ │ Simulator│ │ Completion │  │    │
│  │  │          │ │          │ │ Sliders  │ │ Widget     │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│                            │                                     │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │                   State Layer (React)                     │    │
│  │                                                           │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │    │
│  │  │ Profile Store│ │ Analytics    │ │ Notification     │  │    │
│  │  │ (Zustand)    │ │ Store        │ │ Queue            │  │    │
│  │  │              │ │ (React Query)│ │ (Priority Heap)  │  │    │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘  │    │
│  └─────────────────────────┬───────────────────────────────┘    │
│                            │                                     │
│  ┌─────────────────────────▼───────────────────────────────┐    │
│  │                   Data Layer                              │    │
│  │                                                           │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │    │
│  │  │ REST Client  │ │ WebSocket    │ │ Service Worker   │  │    │
│  │  │ (Axios/Fetch)│ │ Client       │ │ (Offline Cache)  │  │    │
│  │  │              │ │ (Socket.io)  │ │ (IndexedDB)      │  │    │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Backend-for-Frontend (BFF):                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  FastAPI BFF Layer                                        │    │
│  │  • Profile aggregation (calls JSON User Info Generator)   │    │
│  │  • Analytics query proxy (calls Analytics Warehouse)      │    │
│  │  • WebSocket hub (Kafka → client push)                    │    │
│  │  • Personalized card ranking (ML-based priority)          │    │
│  │  • i18n string resolution                                 │    │
│  └─────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Models

### 4.1 Dashboard State Model

```typescript
interface DashboardState {
  profile: UserProfile | null;
  loading: boolean;
  lastUpdated: string;
  
  // Widget states
  widgets: {
    eligibility: EligibilityWidget;
    applications: ApplicationTrackerWidget;
    deadlines: DeadlineCalendarWidget;
    predictions: PredictionWidget;
    heatmap: HeatmapWidget;
    voting: VotingWidget;
    simulator: SimulatorWidget;
    completeness: CompletenessWidget;
  };
  
  // Notification queue (priority-ordered)
  notifications: PriorityNotification[];
  
  // User preferences
  preferences: {
    language: SupportedLanguage;
    theme: 'light' | 'dark' | 'system';
    widgetLayout: WidgetLayoutConfig;
    notificationPrefs: NotificationPreferences;
  };
}

interface EligibilityWidget {
  schemes: EligibleScheme[];
  newSinceLastVisit: number;
  totalPotentialBenefit: number;
  sortBy: 'deadline' | 'benefit' | 'confidence';
}

interface ApplicationTrackerWidget {
  applications: ApplicationStatus[];
  activeCount: number;
  completedCount: number;
  rejectedCount: number;
}

interface PriorityNotification {
  id: string;
  type: 'deadline' | 'eligibility' | 'approval' | 'prediction' | 'voting';
  priority: number;  // 1 (highest) to 5 (lowest)
  title: string;
  body: string;
  actionUrl?: string;
  expiresAt?: string;
  dismissed: boolean;
}

type SupportedLanguage = 
  | 'hi' | 'en' | 'bn' | 'te' | 'mr' | 'ta' 
  | 'gu' | 'ur' | 'kn' | 'ml' | 'or' | 'pa'
  | 'as' | 'mai' | 'sa' | 'kok' | 'sd' | 'ne'
  | 'doi' | 'mni' | 'sat' | 'ks';
```

### 4.2 Widget Configuration

```typescript
interface WidgetLayoutConfig {
  layout: 'default' | 'compact' | 'detailed';
  order: string[];  // Widget IDs in display order
  collapsed: string[];  // Collapsed widget IDs
  pinned: string[];  // Always-visible widget IDs
}

// Default layout priority (personalized by Neural Network Engine)
const DEFAULT_WIDGET_ORDER = [
  'urgent-alerts',      // Overdue deadlines, expiring schemes
  'eligibility-cards',  // New eligible schemes
  'application-tracker',// Active application status
  'deadline-calendar',  // Upcoming deadlines
  'prediction-cards',   // Life event predictions
  'profile-completeness',// Completeness nudge
  'policy-simulator',   // What-if controls
  'civic-heatmap',      // Regional analytics
  'voting-center'       // Election info
];
```

### 4.3 Notification Priority Algorithm

```typescript
function calculateNotificationPriority(notification: RawNotification): number {
  let score = 0;
  
  // Time urgency (exponential as deadline approaches)
  if (notification.deadline) {
    const daysRemaining = daysBetween(new Date(), notification.deadline);
    if (daysRemaining <= 0) score += 100;        // Overdue
    else if (daysRemaining <= 3) score += 80;     // Critical
    else if (daysRemaining <= 7) score += 60;     // Urgent
    else if (daysRemaining <= 30) score += 30;    // Important
    else score += 10;                              // Informational
  }
  
  // Financial impact
  score += Math.min(notification.potentialBenefitINR / 10000, 50);
  
  // Confidence boost
  score += notification.confidence * 20;
  
  // Type multipliers
  const typeMultipliers: Record<string, number> = {
    'deadline_overdue': 1.5,
    'new_eligibility': 1.3,
    'application_update': 1.2,
    'voting_reminder': 1.4,
    'prediction': 0.8
  };
  score *= typeMultipliers[notification.type] ?? 1.0;
  
  return Math.round(score);
}
```

---

## 5. Context Flow

```
┌────────────────────────────────────────────────────────┐
│                    User Interaction                      │
│                                                          │
│  Browser / Mobile PWA / Voice (Riva)                     │
└─────────────────────────┬────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   BFF (Backend for Frontend)             │
│                                                          │
│  1. Authenticate (JWT from API Gateway)                  │
│  2. Fetch assembled profile (JSON User Info Generator)   │
│  3. Fetch analytics cubes (Analytics Warehouse)          │
│  4. Rank widgets by personalized priority                │
│  5. Resolve i18n strings for user language                │
│  6. Establish WebSocket for real-time updates             │
└─────────────────────────┬────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ JSON User    │ │ Analytics    │ │ Neural Net   │
│ Info Gen     │ │ Warehouse    │ │ Engine       │
│              │ │              │ │              │
│ Full profile │ │ Heatmaps,   │ │ Widget       │
│ for user     │ │ trends,     │ │ ranking,     │
│              │ │ cubes       │ │ predictions  │
└──────────────┘ └──────────────┘ └──────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Simulation   │ │ Speech       │ │ Trust        │
│ Engine       │ │ Interface    │ │ Scoring      │
│              │ │              │ │              │
│ "What-if"   │ │ Voice input/ │ │ Confidence   │
│ results     │ │ output       │ │ indicators   │
└──────────────┘ └──────────────┘ └──────────────┘

Real-Time Update Flow:
  Kafka → BFF WebSocket Hub → Browser WebSocket → React State → UI Re-render
```

### Dashboard Rendering Pipeline

| Step | Component | Action | Target |
|---|---|---|---|
| 1 | Service Worker | Check cached profile age | < 5 min → use cache |
| 2 | BFF | Fetch/assemble dashboard data | < 300ms |
| 3 | React | Hydrate state stores | < 50ms |
| 4 | Priority Engine | Rank notifications & widgets | < 20ms |
| 5 | React | Render above-fold widgets | < 100ms (LCP) |
| 6 | React | Lazy-load below-fold widgets | Progressive |
| 7 | WebSocket | Establish real-time connection | < 200ms |
| **Total** | | First Contentful Paint | **< 1.5s** |

---

## 6. Event Bus Integration

### Consumed Events (via WebSocket Hub)

| Event | Source | UI Action |
|---|---|---|
| `profile.delta.generated` | JSON User Info Generator | Patch profile state, animate changed sections |
| `eligibility.new_match` | Eligibility Rules Engine | Show toast notification + new card |
| `deadline.approaching` | Deadline Monitoring Engine | Update countdown timer, escalate priority |
| `simulation.result.ready` | Simulation Engine | Render simulation results in slider widget |
| `analytics.cube.refreshed` | Analytics Warehouse | Refresh heatmap/chart data |
| `trust.score.updated` | Trust Scoring Engine | Update confidence indicators |
| `speech.transcription.ready` | Speech Interface Engine | Display transcribed text, trigger action |

### Published Events (User Actions)

| Event | Trigger | Consumers |
|---|---|---|
| `user.scheme.apply_clicked` | User clicks "Apply" on scheme card | API Gateway → External Gov Portal |
| `user.simulation.requested` | User adjusts "what-if" slider | Simulation Engine |
| `user.profile.data_provided` | User fills missing profile fields | Metadata Engine |
| `user.feedback.submitted` | User rates recommendation quality | Neural Network Engine (RLHF) |
| `user.voice.command` | User speaks voice command | Speech Interface Engine |
| `user.widget.interaction` | User interacts with any widget | Analytics Warehouse (telemetry) |

---

## 7. NVIDIA Stack Alignment

| NVIDIA Tool | Component | Usage |
|---|---|---|
| **Riva** | Voice Navigation | Speech-to-text for voice commands, text-to-speech for accessibility |
| **NIM** | Widget Personalization | Llama 3.1 8B for generating personalized widget descriptions |
| **TensorRT-LLM** | Summary Cards | Optimized inference for profile summary card text |
| **NeMo BERT** | Intent Recognition | Classify user search queries to route to correct widget/action |

### Voice-Enabled Dashboard (Riva Integration)

```typescript
// Voice command handler using NVIDIA Riva
class VoiceDashboardController {
  private rivaClient: RivaStreamingClient;
  
  async handleVoiceCommand(audioStream: ReadableStream): Promise<DashboardAction> {
    // STT via Riva
    const transcript = await this.rivaClient.transcribe(audioStream, {
      language: this.userLanguage,  // e.g., 'hi-IN', 'ta-IN'
      model: 'riva-asr-hindi-citrinet'
    });
    
    // Intent classification via NeMo BERT
    const intent = await this.classifyIntent(transcript.text);
    
    // Route to action
    switch (intent.action) {
      case 'check_eligibility':
        return { type: 'NAVIGATE', widget: 'eligibility-cards' };
      case 'check_deadline':
        return { type: 'NAVIGATE', widget: 'deadline-calendar' };
      case 'simulate':
        return { type: 'OPEN_SIMULATOR', params: intent.entities };
      case 'apply_scheme':
        return { type: 'START_APPLICATION', schemeId: intent.entities.scheme };
      default:
        return { type: 'SEARCH', query: transcript.text };
    }
  }
}
```

---

## 8. Scaling Strategy

| Tier | Users | Strategy |
|---|---|---|
| **MVP** | < 10K | Single BFF instance, React SPA, WebSocket on same server |
| **Growth** | 10K–500K | 3-5 BFF instances with sticky sessions, CDN for static assets, Redis-backed WebSocket adapter |
| **Scale** | 500K–5M | BFF auto-scaling (HPA), WebSocket cluster with Redis pub/sub, edge-cached profile data, PWA offline-first |
| **Massive** | 5M–50M+ | Regional BFF deployments, CDN-rendered personalized pages (edge compute), WebSocket sharding by region, pre-rendered dashboard snapshots |

### Performance Budget

| Metric | Target |
|---|---|
| First Contentful Paint (FCP) | < 1.0s |
| Largest Contentful Paint (LCP) | < 1.5s |
| Time to Interactive (TTI) | < 2.0s |
| Cumulative Layout Shift (CLS) | < 0.1 |
| JavaScript Bundle Size | < 200KB (gzipped) |
| WebSocket Reconnection | < 3s |
| Offline Profile Staleness | < 24 hours |

---

## 9. API Endpoints (BFF)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/dashboard/{user_id}` | Full dashboard data (profile + analytics + notifications) |
| `GET` | `/api/v1/dashboard/{user_id}/notifications` | Priority-sorted notification list |
| `POST` | `/api/v1/dashboard/{user_id}/notifications/{id}/dismiss` | Dismiss notification |
| `GET` | `/api/v1/dashboard/{user_id}/widgets/{widget_id}` | Individual widget data |
| `PUT` | `/api/v1/dashboard/{user_id}/preferences` | Update display preferences |
| `POST` | `/api/v1/dashboard/{user_id}/simulate` | Trigger simulation from slider |
| `WS` | `/ws/dashboard/{user_id}` | WebSocket for real-time updates |
| `GET` | `/api/v1/dashboard/{user_id}/heatmap/{state}` | Civic heatmap data |
| `GET` | `/api/v1/dashboard/{user_id}/calendar` | Deadline calendar feed (iCal compatible) |

---

## 10. Dependencies

### Upstream (Data Sources)

| Engine | Data Provided |
|---|---|
| JSON User Info Generator | Complete assembled profile for user |
| Analytics Warehouse | Pre-computed cubes, heatmaps, trends |
| Neural Network Engine | Personalized widget ranking, predictions |
| Simulation Engine | What-if scenario results |
| Trust Scoring Engine | Confidence indicators for data freshness |
| Speech Interface Engine | Voice transcription, TTS audio |
| Deadline Monitoring Engine | Real-time deadline alerts |

### Downstream (Consumers)

| Engine | Data Consumed |
|---|---|
| Metadata Engine | User-provided profile data (form submissions) |
| Analytics Warehouse | User interaction telemetry |
| Neural Network Engine | User feedback for RLHF training |
| Simulation Engine | Simulation parameter requests |

---

## 11. Technology Stack

| Component | Technology |
|---|---|
| Frontend Framework | React 19.x + TypeScript 5.x |
| Build Tool | Vite 7.x |
| CSS / UI | Tailwind CSS + Radix UI (accessible components) |
| UI Component Libraries | [Hero UI](https://www.heroui.com/docs/components), [ShadCN](https://ui.shadcn.com/), [UIverse](https://uiverse.io/) |
| Map Components | [MapCN](https://www.mapcn.dev/) + MapLibre GL |
| Interactive Buttons | [CSS Buttons](https://cssbuttons.io/) |
| State Management | Zustand (client state) + React Query (server state) |
| Charts / Maps | Recharts (charts) + [MapCN](https://www.mapcn.dev/) + MapLibre GL (maps) |
| WebSocket | Socket.io (client) |
| PWA | Workbox (service worker) + IndexedDB (offline cache) |
| i18n | react-i18next (22 Indian languages) |
| Accessibility | Radix UI + ARIA attributes + axe-core testing |
| BFF | FastAPI (Python) |
| BFF WebSocket | FastAPI WebSocket + Redis pub/sub |
| Testing | Vitest + React Testing Library + Playwright (E2E) |

---

## 12. Implementation Phases

### Phase 1 — Core Dashboard (Weeks 1-3)
- React project setup with Vite + TypeScript + Tailwind
- Profile display from JSON User Info Generator API
- Eligibility alert cards with scheme details
- Application tracker pipeline visualization
- Deadline calendar with countdown timers
- Basic notification queue

### Phase 2 — Interactivity (Weeks 4-5)
- WebSocket integration for real-time profile updates
- Policy simulation slider widget (connected to Simulation Engine)
- Civic heatmap with MapLibre GL
- Profile completeness progress bar with nudges
- Multi-language support (top 8 languages)

### Phase 3 — Intelligence & Voice (Weeks 6-7)
- Personalized widget ranking from Neural Network Engine
- Voice navigation via NVIDIA Riva integration
- AI-generated summary cards (NIM)
- Voting center widget
- WCAG 2.1 AA accessibility audit and fixes

### Phase 4 — Scale & Offline (Weeks 8-9)
- PWA with service worker (Workbox)
- IndexedDB offline profile cache
- CDN optimization for static assets
- Performance audit (LCP < 1.5s, CLS < 0.1)
- Remaining 14 Indian languages
- E2E testing with Playwright

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| LCP (Largest Contentful Paint) | < 1.5s |
| TTI (Time to Interactive) | < 2.0s |
| Profile load success rate | > 99.5% |
| WebSocket connection uptime | > 99% |
| User engagement (daily active / monthly active) | > 25% |
| Notification click-through rate | > 15% |
| Scheme application start rate | > 10% of eligible |
| Profile completeness improvement (post-nudge) | > 20% lift |
| Accessibility score (Lighthouse) | > 95 |
| Offline mode availability | > 99% |
| Voice command success rate | > 80% |
| Multi-language coverage | 22 scheduled languages |

---

## 14. UI Component Libraries

| Library | URL | Usage |
|---|---|---|
| **Hero UI** | https://www.heroui.com/docs/components | Primary component library — cards, modals, inputs, navigation, dropdowns |
| **UIverse** | https://uiverse.io/ | Community-driven UI elements — loaders, toggles, animated components |
| **ShadCN** | https://ui.shadcn.com/ | Copy-paste accessible components — dialogs, command palettes, data tables |
| **CSS Buttons** | https://cssbuttons.io/ | Stylized CTA buttons — apply buttons, simulation triggers, action cards |
| **MapCN** | https://www.mapcn.dev/ | Map components — civic heatmaps, scheme adoption maps, district visualizations |

### Component Mapping

| Dashboard Widget | Preferred Library |
|---|---|
| Eligibility Alert Cards | Hero UI Card + CSS Buttons (CTA) |
| Application Tracker Pipeline | ShadCN Stepper / Progress |
| Deadline Calendar | ShadCN Calendar + Hero UI Badge |
| Policy Simulation Sliders | ShadCN Slider + Hero UI Form |
| Civic Heatmap | MapCN + MapLibre GL |
| Profile Completeness Widget | Hero UI Progress + UIverse animated progress |
| Voting Center | Hero UI Table + ShadCN Card |
| Navigation | ShadCN Command + Hero UI Navbar |
| Notification Queue | Hero UI Toast + ShadCN Alert |
| Impact Prediction Cards | Hero UI Card + UIverse animated counters |

---

## 15. Application Tracking References (MVP)

| Source | URL | Usage |
|---|---|---|
| **UMANG Portal** | https://www.umang.gov.in | Reference structure for public service tracking |
| **DigiLocker** | https://www.digilocker.gov.in | Document verification APIs (requires registration) |
| **DigiLocker Developer API** | https://developer.digilocker.gov.in | API documentation for integration |
