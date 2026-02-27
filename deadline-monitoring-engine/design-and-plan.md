# Deadline Monitoring Engine — Design & Plan

## 1. Purpose

The Deadline Monitoring Engine is the **temporal intelligence layer** that tracks, alerts, and manages time-sensitive civic obligations and opportunities for every citizen. It monitors application deadlines, renewal windows, tax filing dates, scheme enrollment periods, document expiry dates, and election timelines — ensuring no citizen misses a critical deadline due to information asymmetry.

This engine operates as a **continuous time-aware scheduler** that computes deadline proximity, escalates alert priority as deadlines approach, and integrates with the Dashboard Interface for real-time countdown displays and push notifications.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Deadline Detection** | Extract deadlines from scheme definitions, policy updates, and government notifications |
| **Multi-Type Tracking** | Tax filing, scheme application, document renewal, election dates, court hearings |
| **Escalating Alerts** | Progressive urgency: Info (30d) → Important (14d) → Urgent (7d) → Critical (3d) → Overdue |
| **Personalized Calendar** | Per-citizen deadline timeline based on eligible schemes and active documents |
| **Reminder Scheduling** | Configurable reminder schedule (30/14/7/3/1 days before) |
| **Dependency Detection** | Identify deadlines that depend on prior actions (e.g., "File ITR before claiming refund") |
| **Seasonal Pattern Recognition** | Track recurring annual/quarterly deadlines (tax quarters, exam registrations) |
| **Compliance Scoring** | Track citizen's deadline compliance rate over time |
| **Bulk Monitoring** | Evaluate millions of citizen-deadline pairs efficiently |
| **Calendar Export** | iCal feed for native calendar integration |

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Deadline Monitoring Engine                    │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                 Deadline Registry                          │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │ │
│  │  │ Scheme     │  │ Tax        │  │ Document         │    │ │
│  │  │ Deadlines  │  │ Calendar   │  │ Renewals         │    │ │
│  │  │            │  │            │  │                  │    │ │
│  │  │ Enrollment │  │ ITR, GST,  │  │ Aadhaar, PAN,   │    │ │
│  │  │ windows    │  │ Advance Tax│  │ Passport, DL     │    │ │
│  │  └────────────┘  └────────────┘  └──────────────────┘    │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │ │
│  │  │ Election   │  │ Recurring  │  │ Custom User      │    │ │
│  │  │ Dates      │  │ Patterns   │  │ Reminders        │    │ │
│  │  │            │  │            │  │                  │    │ │
│  │  │ Voter reg, │  │ Annual/Qtr │  │ User-created     │    │ │
│  │  │ polling    │  │ recurring  │  │ reminders        │    │ │
│  │  └────────────┘  └────────────┘  └──────────────────┘    │ │
│  └──────────────────────────┬───────────────────────────────┘ │
│                             │                                  │
│  ┌──────────────────────────▼───────────────────────────────┐ │
│  │               Scheduling Engine                            │ │
│  │                                                            │ │
│  │  ┌────────────────────────────────────────────────┐       │ │
│  │  │  Priority Calculator + Cron Evaluator           │       │ │
│  │  │                                                  │       │ │
│  │  │  Every 15 min:                                   │       │ │
│  │  │  - Scan active deadlines                         │       │ │
│  │  │  - Compute days_remaining                        │       │ │
│  │  │  - Escalate priority as needed                   │       │ │
│  │  │  - Trigger notifications for threshold crossings │       │ │
│  │  └────────────────────────────────────────────────┘       │ │
│  └──────────────────────────┬───────────────────────────────┘ │
│                             │                                  │
│  ┌──────────────────────────▼───────────────────────────────┐ │
│  │               Notification Dispatcher                      │ │
│  │                                                            │ │
│  │  In-App │ Push │ SMS │ Email │ WhatsApp │ Calendar feed    │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Data Models

### 4.1 Deadline Definition

```json
{
  "deadline_id": "dl_uuid_v4",
  "type": "scheme_application",
  "category": "government_scheme",
  "title": "PM-KISAN Registration - Kharif Season",
  "description": "Last date to register for PM-KISAN benefits for Kharif 2025 season",
  
  "dates": {
    "deadline": "2025-06-30",
    "window_opens": "2025-04-01",
    "grace_period_end": null
  },
  
  "recurrence": {
    "type": "annual",
    "pattern": "every_year_june_30",
    "next_occurrence": "2026-06-30"
  },
  
  "scope": {
    "states": ["all"],
    "schemes": ["pm_kisan"],
    "demographics": {
      "employment_type": ["farmer"],
      "land_holding": { "lte": 2.0 }
    }
  },
  
  "dependencies": [
    {
      "action": "aadhaar_seeding",
      "description": "Aadhaar must be linked to bank account before applying",
      "estimated_time_days": 7
    }
  ],
  
  "notification_schedule": [30, 14, 7, 3, 1, 0],
  
  "source": {
    "engine": "policy_fetching_engine",
    "url": "https://pmkisan.gov.in",
    "last_verified": "2025-01-10"
  }
}
```

### 4.2 User Deadline Instance

```sql
CREATE TABLE user_deadlines (
    instance_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL,
    deadline_id       VARCHAR(64) NOT NULL,
    deadline_date     DATE NOT NULL,
    
    -- State machine
    status            VARCHAR(20) NOT NULL DEFAULT 'active',
    -- active, notified, acknowledged, completed, missed, deferred
    
    priority          VARCHAR(10) NOT NULL DEFAULT 'info',
    -- info, important, urgent, critical, overdue
    
    days_remaining    INTEGER GENERATED ALWAYS AS (deadline_date - CURRENT_DATE) STORED,
    
    -- Notification tracking
    notifications_sent JSONB DEFAULT '[]',
    last_notified_at   TIMESTAMPTZ,
    next_notification   DATE,
    
    -- User actions
    acknowledged_at    TIMESTAMPTZ,
    completed_at       TIMESTAMPTZ,
    deferred_until     DATE,
    
    -- Metadata
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    updated_at         TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
) PARTITION BY RANGE (deadline_date);

-- Active deadline index for scheduler
CREATE INDEX idx_deadline_active ON user_deadlines (deadline_date, status)
    WHERE status IN ('active', 'notified');

-- User's upcoming deadlines
CREATE INDEX idx_user_deadlines ON user_deadlines (user_id, deadline_date)
    WHERE status NOT IN ('completed', 'missed');
```

### 4.3 Escalation Rules

```python
ESCALATION_THRESHOLDS = {
    "info":      {"days_range": (31, 365), "color": "blue",   "weight": 1},
    "important": {"days_range": (15, 30),  "color": "yellow", "weight": 2},
    "urgent":    {"days_range": (4, 14),   "color": "orange", "weight": 4},
    "critical":  {"days_range": (1, 3),    "color": "red",    "weight": 8},
    "overdue":   {"days_range": (-365, 0), "color": "black",  "weight": 16},
}

def compute_priority(days_remaining: int) -> str:
    for priority, config in ESCALATION_THRESHOLDS.items():
        low, high = config["days_range"]
        if low <= days_remaining <= high:
            return priority
    return "info"
```

### 4.4 Compliance Score

```json
{
  "user_id": "usr_123",
  "compliance_score": 0.85,
  "total_deadlines_tracked": 24,
  "completed_on_time": 18,
  "completed_late": 3,
  "missed": 2,
  "active": 1,
  "streak_current_days": 45,
  "streak_best_days": 120,
  "risk_level": "low",
  "computed_at": "2025-01-15T10:30:00Z"
}
```

---

## 5. Context Flow

```
Data Sources:
  ┌──────────────────────────┐
  │ Policy Fetching Engine   │──▶ Scheme deadlines, enrollment windows
  │ Gov Data Sync Engine     │──▶ Amended deadlines, new announcements
  │ Eligibility Rules Engine │──▶ Schemes user is eligible for (scope filtering)
  │ Identity Engine          │──▶ Document expiry dates
  │ Tax Calendar (Static)    │──▶ ITR, GST, advance tax deadlines
  │ Election Commission      │──▶ Election dates, voter registration
  └──────────────────────────┘
              │
              ▼
  ┌──────────────────────────────────┐
  │ Deadline Ingestion Pipeline      │
  │                                  │
  │ 1. Parse deadline from source    │
  │ 2. Deduplicate (same deadline?)  │
  │ 3. Validate date & scope         │
  │ 4. Store in Deadline Registry    │
  │ 5. Match against eligible users  │
  └──────────────┬───────────────────┘
                 │
  ┌──────────────▼───────────────────┐
  │ User-Deadline Matching           │
  │                                  │
  │ For each new/updated deadline:   │
  │   Find users where:              │
  │   - User's state ∈ deadline.scope│
  │   - User eligible for scheme     │
  │   - Deadline not already tracked │
  │                                  │
  │ Create user_deadline instances   │
  └──────────────┬───────────────────┘
                 │
  ┌──────────────▼───────────────────┐
  │ Scheduler (Every 15 minutes)     │
  │                                  │
  │ SELECT * FROM user_deadlines     │
  │ WHERE status IN ('active',       │
  │   'notified')                    │
  │ AND deadline_date BETWEEN        │
  │   NOW() AND NOW() + 30 days     │
  │                                  │
  │ For each:                        │
  │   1. Compute days_remaining      │
  │   2. Compute new priority        │
  │   3. Check notification schedule │
  │   4. Emit alert if threshold     │
  │      crossed                     │
  └──────────────┬───────────────────┘
                 │
  ┌──────────────▼───────────────────┐
  │ Notification Dispatcher          │
  │                                  │
  │ Channel selection by priority:   │
  │   info      → In-app only       │
  │   important → In-app + email    │
  │   urgent    → In-app + push     │
  │   critical  → All channels      │
  │   overdue   → All + escalation  │
  └──────────────────────────────────┘
```

---

## 6. Event Bus Integration

### Consumed Events

| Event | Source | Action |
|---|---|---|
| `policy.deadline.detected` | Policy Fetching Engine | Create new deadline in registry |
| `policy.deadline.amended` | Government Data Sync Engine | Update existing deadline dates |
| `eligibility.computed` | Eligibility Rules Engine | Match eligible users to scheme deadlines |
| `identity.document.expiring` | Identity Engine | Track document renewal deadlines |
| `user.deadline.acknowledged` | Dashboard Interface | Mark deadline as acknowledged |
| `user.deadline.completed` | Dashboard/External | Mark deadline as completed |

### Published Events

| Event | Payload | Consumers |
|---|---|---|
| `deadline.detected` | `{ user_id, deadline_id, deadline_date, type, priority }` | JSON User Info Generator, Dashboard |
| `deadline.approaching` | `{ user_id, deadline_id, days_remaining, priority }` | Dashboard (countdown update) |
| `deadline.escalated` | `{ user_id, deadline_id, old_priority, new_priority }` | Dashboard, Notification Service |
| `deadline.missed` | `{ user_id, deadline_id, consequence }` | Dashboard, Analytics, Neural Network |
| `deadline.outcome` | `{ user_id, deadline_id, outcome: completed/missed }` | Analytics Warehouse |

---

## 7. NVIDIA Stack Alignment

| NVIDIA Tool | Component | Usage |
|---|---|---|
| **NIM** | Deadline Extraction | Llama 3.1 8B extracts deadline dates from unstructured policy text |
| **NeMo BERT** | Date NER | Named Entity Recognition for date extraction and normalization |
| **TensorRT-LLM** | Reminder Text | Generate personalized reminder messages in user's language |
| **RAPIDS cuDF** | Batch Processing | GPU-accelerated batch evaluation of millions of user-deadline pairs |

### Date Extraction from Policy Text

```python
async def extract_deadlines_from_text(policy_text: str) -> list[dict]:
    """Use NeMo BERT NER + Llama 3.1 8B to extract deadline information."""
    
    # Step 1: NER for date entities
    date_entities = await nemo_ner.extract(
        text=policy_text,
        entity_types=["DATE", "DEADLINE", "DURATION"]
    )
    
    # Step 2: Llama contextualizes the dates
    prompt = f"""
    Extract deadline information from this government policy text.
    
    Text: {policy_text}
    
    Detected dates: {date_entities}
    
    For each deadline found, return JSON:
    {{
      "deadline_type": "application|renewal|filing|registration",
      "date": "YYYY-MM-DD",
      "description": "what must be done by this date",
      "recurring": true/false,
      "recurrence_pattern": "annual|quarterly|monthly|null"
    }}
    """
    
    response = await nim_client.generate(
        model="meta/llama-3.1-8b-instruct",
        prompt=prompt,
        max_tokens=500,
        temperature=0.1
    )
    return parse_json_array(response.text)
```

---

## 8. Scaling Strategy

| Tier | Users | Strategy |
|---|---|---|
| **MVP** | < 10K | Single scheduler cron job (every 15 min), PostgreSQL, basic email/in-app |
| **Growth** | 10K–500K | Distributed scheduler (Celery Beat), Redis deadline queue, push notifications |
| **Scale** | 500K–5M | Partitioned deadline table by month, RAPIDS batch evaluation, multi-channel notifications |
| **Massive** | 5M–50M+ | Pre-computed deadline priority queues in Redis, regional schedulers, RAPIDS GPU for nightly sweep |

---

## 9. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/deadlines/{user_id}` | All active deadlines for user |
| `GET` | `/api/v1/deadlines/{user_id}/upcoming?days=30` | Deadlines within N days |
| `GET` | `/api/v1/deadlines/{user_id}/overdue` | Overdue deadlines |
| `POST` | `/api/v1/deadlines/{user_id}/{deadline_id}/acknowledge` | Acknowledge a deadline |
| `POST` | `/api/v1/deadlines/{user_id}/{deadline_id}/complete` | Mark as completed |
| `POST` | `/api/v1/deadlines/{user_id}/{deadline_id}/defer` | Defer/snooze deadline |
| `GET` | `/api/v1/deadlines/{user_id}/compliance` | Get compliance score |
| `GET` | `/api/v1/deadlines/{user_id}/calendar.ics` | iCal feed export |
| `GET` | `/api/v1/deadlines/registry` | List all system-wide deadlines |

---

## 10. Dependencies

### Upstream

| Engine | Data Provided |
|---|---|
| Policy Fetching Engine | Scheme deadline dates, enrollment windows |
| Government Data Sync Engine | Amended deadlines, new government notifications |
| Eligibility Rules Engine | User eligibility (determines which deadlines apply) |
| Identity Engine | Document expiry dates (passport, DL, etc.) |

### Downstream

| Engine | Data Consumed |
|---|---|
| JSON User Info Generator | Upcoming/overdue deadlines for profile assembly |
| Dashboard Interface | Countdown timers, calendar view, alert cards |
| Neural Network Engine | Deadline context for proactive recommendations |
| Analytics Warehouse | Deadline compliance statistics |
| Notification Service | Multi-channel deadline reminders |

---

## 11. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| Scheduler | Celery Beat + Redis (distributed scheduling) |
| Database | PostgreSQL 16 (deadline registry + user instances) |
| Cache | Redis 7.x (notification queue, priority cache) |
| Event Bus | Apache Kafka |
| Calendar | icalendar (Python library for iCal export) |
| Notifications | Firebase Cloud Messaging (push), Amazon SES (email), Twilio (SMS) |
| NLP | NVIDIA NIM + NeMo BERT (deadline extraction) |
| Monitoring | Prometheus + Grafana |

---

## 12. Implementation Phases

### Phase 1 — Foundation (Weeks 1-2)
- PostgreSQL deadline registry and user_deadlines tables
- Static deadline ingestion (tax calendar, known scheme deadlines)
- Priority computation with escalation thresholds
- Basic scheduler (every 15 min) for deadline evaluation

### Phase 2 — Notifications (Weeks 3-4)
- Kafka integration for upstream events
- Multi-channel notification dispatcher (in-app, email, push)
- Notification scheduling (30/14/7/3/1 day reminders)
- iCal feed generation for calendar export

### Phase 3 — Intelligence (Weeks 5-6)
- NLP deadline extraction from policy text (NIM + NeMo BERT)
- Dependency detection (prerequisite actions before deadline)
- Compliance scoring algorithm
- Personalized reminder text generation

### Phase 4 — Scale (Weeks 7-8)
- RAPIDS batch evaluation for millions of user-deadline pairs
- Partitioned tables for deadline archiving
- Regional scheduler distribution
- WhatsApp notification channel integration
- Performance target: 50M user-deadline evaluations in < 30 minutes

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Deadline detection accuracy | > 95% |
| Notification delivery rate | > 99% |
| Scheduler execution latency | < 5 minutes (full sweep) |
| User deadline miss rate (post-notification) | < 5% |
| Compliance score improvement (90-day) | > 30% lift |
| Push notification open rate | > 25% |
| Calendar export adoption | > 10% of users |
| False deadline alerting rate | < 1% |
| Deadline coverage (schemes with tracked deadlines) | > 85% |
| Overdue escalation time | < 1 hour |

---

## 14. Official Data Sources (MVP)

| Data Required | Official Source | URL | Notes |
|---|---|---|---|
| Scheme deadlines, enrollment windows | Open Government Data Portal | https://data.gov.in | Extract from scheme metadata CSVs |
| Tax filing deadlines, due dates | Income Tax Portal | https://www.incometax.gov.in | ITR, advance tax, TDS quarterly dates |
| Election deadlines, voter registration | Election Commission India | https://eci.gov.in | Polling dates, voter ID updates |
| Gazette notification deadlines | eGazette | https://egazette.nic.in | Compliance deadlines from notifications |

### Deadline Calendar Seed Data

| Category | Example Deadlines | Source |
|---|---|---|
| **Tax** | ITR filing (31 Jul), Advance Tax (15 Jun/Sep/Dec/Mar), GST returns | incometax.gov.in |
| **Schemes** | PM-KISAN registration, PMAY application, scholarship deadlines | data.gov.in |
| **Documents** | Aadhaar update, PAN-Aadhaar linking, Passport renewal | uidai.gov.in, incometax.gov.in |
| **Elections** | Voter registration, polling dates | eci.gov.in |
| **Financial** | EPF withdrawal, PPF maturity, LIC premium | respective portals |

---

## 14. Security Hardening

### 14.1 Rate Limiting

<!-- SECURITY: Deadline monitoring has notification-triggering endpoints.
     Rate limits prevent notification spam and calendar abuse.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  # SECURITY: Get user deadlines — standard read
  "/api/v1/deadlines":
    per_user:
      requests_per_minute: 30
      burst: 10

  # SECURITY: Snooze/dismiss deadline — state mutation
  "/api/v1/deadlines/{deadline_id}/snooze":
    per_user:
      requests_per_minute: 10
      burst: 3

  # SECURITY: Custom deadline creation
  "/api/v1/deadlines/custom":
    per_user:
      requests_per_minute: 5
      burst: 2
    max_custom_deadlines_per_user: 50  # Prevent storage abuse

  # SECURITY: Notification preferences update
  "/api/v1/deadlines/preferences":
    per_user:
      requests_per_minute: 5

  # SECURITY: Internal deadline sync (from Government Data Sync Engine)
  internal_endpoints:
    "/internal/deadlines/sync":
      per_service:
        requests_per_minute: 60
      allowed_callers: ["government-data-sync-engine", "policy-fetching-engine"]

  rate_limit_response:
    status: 429
    body:
      error: "rate_limit_exceeded"
      message: "Deadline service rate limit reached."
```

### 14.2 Input Validation & Sanitization

<!-- SECURITY: Custom deadlines accept user-provided dates and descriptions.
     Validation prevents injection and invalid date exploits.
     OWASP Reference: API3:2023, API8:2023 -->

```python
# SECURITY: Custom deadline creation schema
CUSTOM_DEADLINE_SCHEMA = {
    "type": "object",
    "required": ["title", "deadline_date", "category"],
    "additionalProperties": False,
    "properties": {
        "title": {
            "type": "string",
            "minLength": 3,
            "maxLength": 200,
            "pattern": "^[\\w\\s\\-.,()]+$"  # Alphanumeric + basic punctuation
        },
        "description": {
            "type": "string",
            "maxLength": 1000
        },
        "deadline_date": {
            "type": "string",
            "format": "date",
            "description": "Must be a future date"
        },
        "category": {
            "type": "string",
            "enum": ["tax", "scheme", "document", "financial", "election", "custom"]
        },
        "reminder_schedule": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "days_before": {"type": "integer", "minimum": 0, "maximum": 365},
                    "channel": {"type": "string", "enum": ["push", "sms", "email", "whatsapp"]}
                }
            }
        }
    }
}

# SECURITY: Date validation — prevent past-date and far-future abuse
def validate_deadline_date(date_str: str) -> bool:
    from datetime import date, timedelta
    deadline = date.fromisoformat(date_str)
    today = date.today()
    max_future = today + timedelta(days=365 * 5)  # Max 5 years ahead
    return today < deadline <= max_future
```

### 14.3 Secure API Key & Secret Management

```yaml
secrets_management:
  environment_variables:
    - DB_PASSWORD               # PostgreSQL (deadline records)
    - REDIS_PASSWORD            # Reminder scheduling cache
    - KAFKA_SASL_PASSWORD       # Event bus auth
    - SMS_GATEWAY_KEY           # Notification SMS (MSG91/Twilio)
    - PUSH_NOTIFICATION_KEY     # Firebase Cloud Messaging key
    - EMAIL_SMTP_PASSWORD       # Email notification service
    - WHATSAPP_API_KEY          # WhatsApp Business API

  rotation_policy:
    db_credentials: 90_days
    notification_keys: 180_days
    service_tokens: 90_days

  # SECURITY: Notification keys are extremely sensitive — can send to any user
  notification_key_protection:
    restricted_to_notification_service: true
    never_exposed_via_api: true
    usage_logging: true  # Log every notification sent
```

### 14.4 OWASP Compliance

| OWASP Risk | Mitigation |
|---|---|
| **API1: BOLA** | Users can only view/modify their own deadlines; admin for cross-user |
| **API2: Broken Auth** | JWT validation; notification preferences require re-auth |
| **API3: Broken Property Auth** | Custom deadline schema with category enum; no arbitrary fields |
| **API4: Resource Consumption** | Max 50 custom deadlines per user; reminder schedule capped at 5 |
| **API5: Broken Function Auth** | Internal sync endpoints restricted to service tokens |
| **API6: Sensitive Flows** | Notification preference changes require re-authentication |
| **API7: SSRF** | No URL inputs; deadlines sourced from internal sync only |
| **API8: Misconfig** | Notification keys isolated from API layer; never in responses |
| **API9: Improper Inventory** | Deadline sources tracked with provenance; synced deadlines versioned |
| **API10: Unsafe Consumption** | Government deadline data validated against schema before storage |

---

## ⚙️ Build Phase Instructions (Current Phase Override)

> **These instructions override any conflicting guidance above for the current local build phase.**

### 1. Local-First Architecture
- Build and run this engine **entirely locally**. Do NOT integrate any AWS cloud services (Amazon SES, Firebase Cloud Messaging, etc.).
- All references to cloud infrastructure are deferred to the cloud migration phase.
- Use local Celery Beat with Redis (local) for scheduling.

### 2. Data Storage & Caching (Zero-Redundancy)
- Before downloading or fetching any external data/files, **always check if the target data already exists locally**.
- If present locally → skip the download and load directly from the local path.
- Only download/fetch data if it is **completely missing locally**.
- Cache deadline data locally in PostgreSQL/Redis.

### 3. Deferred Features (Do NOT Implement Yet)
- **Notifications & Messaging**: Do NOT implement any notification delivery systems. This includes:
  - SMS notifications (Twilio, MSG91, `SMS_GATEWAY_KEY`)
  - Email notifications (Amazon SES, SMTP, `EMAIL_SMTP_PASSWORD`)
  - Push notifications (FCM, `PUSH_NOTIFICATION_KEY`)
  - WhatsApp notifications (`WHATSAPP_API_KEY`)
  - In-app toast/bell notifications
- Instead, **log all notification events to a local notifications table** (store: user_id, message, channel, timestamp, deadline_id). This table will be consumed by notification services when they are built later.
- Skip `SMS_GATEWAY_KEY`, `PUSH_NOTIFICATION_KEY`, `EMAIL_SMTP_PASSWORD`, `WHATSAPP_API_KEY` — do not configure or use these.

### 4. Primary Focus
Build a robust, locally-functioning deadline monitoring engine with:
- Deadline extraction and tracking from policy data
- Temporal intelligence (recurring vs one-time deadlines)
- Custom user deadline management
- Escalating reminder schedule computation (stored, not delivered)
- Deadline sync from government sources (data.gov.in, etc.)
- All functionality testable without any external notification or cloud dependencies
