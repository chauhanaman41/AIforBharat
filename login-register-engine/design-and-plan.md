# 🟦 Login / Register Engine — Design & Plan

## 1. Purpose

The Login/Register Engine is the **user onboarding gateway** for the AIforBharat platform. It handles new user registration, credential-based authentication, session generation, and future integration with India's digital identity infrastructure (Aadhaar, PAN, DigiLocker).

This engine is the first touchpoint for every user and must be **fast, secure, and frictionless** — especially for rural and semi-urban users who may have limited digital literacy.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **User Registration** | Collect minimal identity info (phone/email, name, state, preferred language) |
| **Credential Authentication** | Phone OTP, email/password, or social login |
| **Session Generation** | Issue JWT access + refresh tokens upon successful auth |
| **OAuth2 Support** | Standards-based auth flow for third-party integrations |
| **Aadhaar/PAN Linking** | Future: eKYC via Aadhaar, PAN verification for financial features |
| **DigiLocker Integration** | Future: Pull verified documents for eligibility checks |
| **Multi-Language Onboarding** | Registration flow available in 12+ Indian languages |
| **Rate Limiting** | Brute-force protection on login/OTP endpoints |
| **Audit Logging** | Every auth event logged immutably to Raw Data Store |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     User (Web / Mobile / Voice)              │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTPS
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Rate Limiter│  │ TLS Termination│ │ Request Validator │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                  Login/Register Engine                        │
│                                                              │
│  ┌────────────────┐  ┌──────────────────┐                    │
│  │ Registration   │  │ Authentication   │                    │
│  │ Service        │  │ Service          │                    │
│  │                │  │                  │                    │
│  │ • Validate     │  │ • Verify creds   │                    │
│  │ • Deduplicate  │  │ • Generate JWT   │                    │
│  │ • Create user  │  │ • Refresh tokens │                    │
│  └───────┬────────┘  └───────┬──────────┘                    │
│          │                   │                               │
│  ┌───────▼───────────────────▼──────────┐                    │
│  │         OTP / SMS Gateway            │                    │
│  │    (Twilio / MSG91 / Custom)         │                    │
│  └──────────────────────────────────────┘                    │
│                                                              │
│  ┌──────────────────────────────────────┐                    │
│  │     Identity Engine Delegate         │                    │
│  │  (Forward identity ops after auth)   │                    │
│  └──────────────────────────────────────┘                    │
└──────────────────────┬───────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ User DB      │ │ Redis    │ │ Raw Data     │
│ (PostgreSQL) │ │ (Session │ │ Store        │
│              │ │  Cache)  │ │ (Audit Log)  │
└──────────────┘ └──────────┘ └──────────────┘
```

### 3.2 Stateless Design

- **No server-side sessions** — all session state is encoded in JWT tokens
- Authentication service is **horizontally scalable** behind a load balancer
- OTP state stored in **Redis with TTL** (5-minute expiry)
- User creation is an **idempotent operation** keyed on phone number

---

## 4. Data Models

### 4.1 User Registration Payload

```json
{
  "phone": "+91XXXXXXXXXX",
  "name": "Ravi Kumar",
  "state": "UP",
  "district": "Lucknow",
  "preferred_language": "hi",
  "registration_source": "web",
  "consent_given": true,
  "consent_timestamp": "2026-02-26T10:00:00Z"
}
```

### 4.2 JWT Token Structure

```json
{
  "sub": "user_uuid_v4",
  "iat": 1740000000,
  "exp": 1740003600,
  "role": "citizen",
  "region": "UP",
  "scopes": ["read:schemes", "write:profile"],
  "token_type": "access"
}
```

### 4.3 Auth Event Log (to Raw Data Store)

```json
{
  "event_id": "evt_uuid",
  "user_id": "user_uuid",
  "event_type": "LOGIN_SUCCESS",
  "timestamp": "2026-02-26T10:05:00Z",
  "ip_address": "hashed",
  "device_fingerprint": "hashed",
  "region": "UP"
}
```

---

## 5. Context Flow

```
User opens app
    │
    ├─► [New User] → Registration Form
    │       │
    │       ├─► Validate phone → Send OTP (via SMS Gateway)
    │       ├─► User enters OTP → Verify against Redis
    │       ├─► Create user record in PostgreSQL
    │       ├─► Publish USER_REGISTERED event to Event Bus
    │       ├─► Forward identity setup to Identity Engine
    │       └─► Issue JWT tokens → Return to client
    │
    └─► [Existing User] → Login Form
            │
            ├─► Phone + OTP flow  OR  Email + Password flow
            ├─► Verify credentials
            ├─► Publish LOGIN_SUCCESS event to Event Bus
            ├─► Issue JWT tokens → Return to client
            └─► Failed? → Log LOGIN_FAILED event, increment rate counter
```

---

## 6. Event Bus Integration

| Event | Payload | Consumers |
|---|---|---|
| `USER_REGISTERED` | `{user_id, phone, state, timestamp}` | Identity Engine, Metadata Engine, Analytics |
| `LOGIN_SUCCESS` | `{user_id, timestamp, device}` | Raw Data Store, Analytics |
| `LOGIN_FAILED` | `{phone, reason, timestamp}` | Anomaly Detection, Raw Data Store |
| `TOKEN_REFRESHED` | `{user_id, timestamp}` | Raw Data Store |
| `ACCOUNT_LOCKED` | `{user_id, reason, timestamp}` | Identity Engine, Anomaly Detection |

---

## 7. NVIDIA Stack Alignment

| Component | NVIDIA Tool | Usage |
|---|---|---|
| OTP Verification | — | Standard crypto, no GPU needed |
| Captcha / Bot Detection | NVIDIA Morpheus | Anomaly detection on auth patterns |
| Future: Voice Auth | NVIDIA Riva | Speaker verification for voice login |
| Future: Face Auth | NVIDIA DeepStream | Liveness detection for eKYC |

---

## 8. Scaling Strategy

| Scale Tier | Users | Strategy |
|---|---|---|
| **Tier 1** (MVP) | < 10K | Single instance, SQLite → PostgreSQL |
| **Tier 2** | 10K – 1M | Horizontal pods, Redis cluster, read replicas |
| **Tier 3** | 1M – 10M | Multi-region, geo-DNS routing, regional DB shards |
| **Tier 4** | 10M+ | Edge auth nodes, precomputed OTP pools, CDN-based static auth pages |

### Key Scaling Decisions

- **Redis Cluster** for distributed session/OTP cache
- **PostgreSQL with Citus** for horizontal user table sharding (shard key: `region`)
- **Connection pooling** via PgBouncer
- **Auth service replicas**: min 3, auto-scale on CPU/request latency

---

## 9. Security Considerations

| Concern | Mitigation |
|---|---|
| Brute-force attacks | Rate limiting (5 attempts / 15 min), exponential backoff |
| Token theft | Short-lived access tokens (1hr), HTTPOnly refresh cookies |
| OTP interception | OTP hash stored in Redis, not in DB; 5-min expiry |
| Data breach | Passwords bcrypt-hashed (cost=12); PII encrypted at rest |
| Session hijacking | Device fingerprint binding in JWT |
| CSRF | SameSite cookies + CSRF token for state-changing requests |

---

## 10. API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/login` | Login with credentials |
| `POST` | `/api/v1/auth/otp/send` | Send OTP to phone |
| `POST` | `/api/v1/auth/otp/verify` | Verify OTP code |
| `POST` | `/api/v1/auth/token/refresh` | Refresh access token |
| `POST` | `/api/v1/auth/logout` | Invalidate session |
| `GET`  | `/api/v1/auth/me` | Get current user profile |
| `PUT`  | `/api/v1/auth/profile` | Update user profile |

---

## 11. Dependencies

| Dependency | Direction | Purpose |
|---|---|---|
| **Identity Engine** | Downstream | Delegates identity vault creation after registration |
| **Metadata Engine** | Downstream | Triggers user profile enrichment |
| **Raw Data Store** | Downstream | Logs all auth events immutably |
| **Event Bus** | Downstream | Publishes auth lifecycle events |
| **API Gateway** | Upstream | Receives all auth requests through gateway |
| **Anomaly Detection** | Downstream | Monitors for suspicious auth patterns |

---

## 12. Technology Stack

| Layer | Technology |
|---|---|
| Runtime | Node.js 20 LTS / Python 3.11 (FastAPI) |
| Auth Protocol | OAuth2 + JWT (RS256) |
| Password Hashing | bcrypt (cost factor 12) |
| OTP Cache | Redis 7.x (TTL-based) |
| User Storage | PostgreSQL 16 |
| SMS Gateway | MSG91 / Twilio / AWS SNS |
| Event Bus | Apache Kafka / NATS |
| Containerization | Docker + Kubernetes |
| Monitoring | Prometheus + Grafana |

---

## 13. Implementation Phases

| Phase | Milestone | Timeline |
|---|---|---|
| **Phase 1** | Phone + OTP registration/login, JWT auth | Week 1-2 |
| **Phase 2** | Email/password auth, profile management | Week 3 |
| **Phase 3** | Rate limiting, audit logging, anomaly hooks | Week 4 |
| **Phase 4** | DigiLocker / Aadhaar integration (sandbox) | Week 6-8 |
| **Phase 5** | Voice-based auth via Riva | Week 10-12 |

---

## 14. Success Metrics

| Metric | Target |
|---|---|
| Registration completion rate | > 85% |
| Login latency (P95) | < 200ms |
| OTP delivery success rate | > 98% |
| Failed login detection accuracy | > 95% |
| Token refresh success rate | > 99.5% |

---

## 15. Identity & Authentication References (MVP)

| Service | URL | Purpose |
|---|---|---|
| **Aadhaar (UIDAI)** | https://uidai.gov.in | Public stats — eKYC requires government approval |
| **DigiLocker** | https://www.digilocker.gov.in | Pull verified documents post-registration |
| **DigiLocker Developer API** | https://developer.digilocker.gov.in | OAuth2-based document access API |
| **UMANG** | https://web.umang.gov.in | Reference for unified service authentication |

> ⚠️ **Important:** Full Aadhaar-based authentication (eKYC) requires UIDAI licensing. MVP phase uses Phone OTP + Email/Password. DigiLocker integration is planned for Phase 4.

---

## 16. Security Hardening

### 16.1 Rate Limiting (Per-Endpoint)

<!-- SECURITY: Auth endpoints are the most targeted attack surface.
     Rate limits are IP-based for unauthenticated endpoints, user-based post-login.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  # SECURITY: OTP send — strictest limit to prevent SMS bombing
  "/api/v1/auth/otp/send":
    per_ip:
      requests_per_minute: 3
      requests_per_hour: 10
      burst: 1
    per_phone:  # Keyed on phone number
      requests_per_minute: 1
      requests_per_hour: 5
      cooldown_seconds: 60  # Minimum 60s between OTP sends

  # SECURITY: OTP verify — prevent brute-force
  "/api/v1/auth/otp/verify":
    per_ip:
      requests_per_minute: 5
      burst: 2
    per_phone:
      max_attempts_per_otp: 3  # Lock OTP after 3 wrong attempts
      lockout_duration_minutes: 15

  # SECURITY: Login — progressive delay after failures
  "/api/v1/auth/login":
    per_ip:
      requests_per_minute: 10
      burst: 3
    per_account:  # Keyed on phone/email
      max_failed_attempts: 5
      lockout_duration_minutes: 15
      progressive_delay: true  # 1s, 2s, 4s, 8s, 16s delay

  # SECURITY: Registration — prevent automated account creation
  "/api/v1/auth/register":
    per_ip:
      requests_per_minute: 3
      requests_per_hour: 10
    captcha_required_after: 2  # Require CAPTCHA after 2 registrations from same IP

  # SECURITY: Token refresh — prevent token farming
  "/api/v1/auth/token/refresh":
    per_user:
      requests_per_minute: 5
      burst: 2

  # SECURITY: Graceful 429 response
  rate_limit_response:
    status: 429
    body:
      error: "rate_limit_exceeded"
      message: "Too many attempts. Please wait before trying again."
      retry_after_seconds: "<computed>"
    headers:
      Retry-After: "<seconds>"
```

### 16.2 Input Validation & Sanitization

<!-- SECURITY: Every input field is validated against a strict schema.
     No raw user input reaches the database without sanitization.
     OWASP Reference: API3:2023, API8:2023 -->

```python
# SECURITY: Registration input schema — reject unexpected fields
REGISTRATION_SCHEMA = {
    "type": "object",
    "required": ["phone", "name", "state", "consent_given"],
    "additionalProperties": False,  # SECURITY: Reject any field not in schema
    "properties": {
        "phone": {
            "type": "string",
            "pattern": "^\\+91[6-9][0-9]{9}$",  # Valid Indian mobile number
            "description": "Must be a valid +91 Indian mobile number"
        },
        "name": {
            "type": "string",
            "minLength": 2,
            "maxLength": 100,
            "pattern": "^[\\p{L}\\p{M}\\s.'-]+$",  # Unicode letters, spaces, hyphens
            "description": "No special characters, SQL, or script tags"
        },
        "state": {
            "type": "string",
            "enum": ["AP","AR","AS","BR","CG","GA","GJ","HR","HP","JH","KA","KL","MP","MH","MN","ML","MZ","NL","OD","PB","RJ","SK","TN","TS","TR","UP","UK","WB","AN","CH","DN","DD","DL","JK","LA","LD","PY"]
        },
        "district": {
            "type": "string",
            "maxLength": 64,
            "pattern": "^[a-zA-Z\\s-]+$"
        },
        "preferred_language": {
            "type": "string",
            "enum": ["hi","en","bn","te","mr","ta","gu","ur","kn","ml","or","pa","as","mai"]
        },
        "registration_source": {
            "type": "string",
            "enum": ["web", "mobile", "voice", "kiosk"]
        },
        "consent_given": {
            "type": "boolean",
            "const": True  # SECURITY: Consent must be explicitly true
        },
        "consent_timestamp": {
            "type": "string",
            "format": "date-time"
        }
    }
}

# SECURITY: Login input schema
LOGIN_SCHEMA = {
    "type": "object",
    "required": ["phone"],
    "additionalProperties": False,
    "properties": {
        "phone": {
            "type": "string",
            "pattern": "^\\+91[6-9][0-9]{9}$"
        },
        "password": {
            "type": "string",
            "minLength": 8,
            "maxLength": 128  # Prevent bcrypt DoS with extremely long passwords
        }
    }
}

# SECURITY: OTP input — exactly 6 digits, no injection
OTP_SCHEMA = {
    "type": "object",
    "required": ["phone", "otp"],
    "additionalProperties": False,
    "properties": {
        "phone": {
            "type": "string",
            "pattern": "^\\+91[6-9][0-9]{9}$"
        },
        "otp": {
            "type": "string",
            "pattern": "^[0-9]{6}$"  # Exactly 6 digits
        }
    }
}

# SECURITY: Sanitization middleware applied before schema validation
def sanitize_input(payload: dict) -> dict:
    """Strip dangerous patterns from all string fields."""
    for key, value in payload.items():
        if isinstance(value, str):
            value = value.strip()
            value = value.replace('\x00', '')    # Null byte injection
            value = html.escape(value)            # XSS prevention
            # SECURITY: Reject if contains SQL/NoSQL injection patterns
            if re.search(r"(--|;|'|\"|--)|(\$ne|\$gt|\$regex)", value, re.I):
                raise ValidationError(f"Invalid characters in field: {key}")
            payload[key] = value
    return payload
```

### 16.3 Secure API Key & Secret Management

<!-- SECURITY: SMS gateway keys, JWT signing keys, and DB credentials
     are NEVER hard-coded. All loaded from environment or secrets manager.
     OWASP Reference: API1:2023 -->

```yaml
secrets_management:
  # SECURITY: All secrets via environment variables — never in code or config files
  environment_variables:
    - SMS_GATEWAY_API_KEY       # MSG91/Twilio API key for OTP delivery
    - SMS_GATEWAY_SENDER_ID     # Sender ID for SMS
    - JWT_PRIVATE_KEY           # RS256 private key for token signing
    - JWT_PUBLIC_KEY            # RS256 public key for token verification
    - DB_PASSWORD               # PostgreSQL password
    - REDIS_PASSWORD            # Redis password for OTP/session cache
    - KAFKA_SASL_PASSWORD       # Event bus auth
    - DIGILOCKER_CLIENT_ID      # DigiLocker OAuth2 client (future Phase 4)
    - DIGILOCKER_CLIENT_SECRET  # DigiLocker OAuth2 secret (future Phase 4)

  rotation_policy:
    sms_gateway_key: 90_days
    jwt_signing_keys: 90_days   # Rotate with grace period for old tokens
    db_credentials: 90_days
    digilocker_credentials: 180_days

  # SECURITY: Never expose secrets in responses, logs, or error messages
  redaction:
    - log_pattern: "otp=[0-9]+"
      replace: "otp=[REDACTED]"
    - log_pattern: "password=.*"
      replace: "password=[REDACTED]"
    - log_pattern: "Bearer [A-Za-z0-9._-]+"
      replace: "Bearer [REDACTED]"

  # SECURITY: Client-side — no keys, tokens, or secrets in frontend code
  client_side:
    jwt_access_token: "stored in memory only, never localStorage"
    jwt_refresh_token: "HTTPOnly, Secure, SameSite=Strict cookie"
    no_api_keys_in_frontend: true
```

### 16.4 OWASP Compliance Checklist

| OWASP Risk | Status | Implementation |
|---|---|---|
| **API1: BOLA** | ✅ | Users can only access their own profile via JWT `sub` claim |
| **API2: Broken Auth** | ✅ | RS256 JWT, bcrypt (cost=12), OTP via SMS, device binding |
| **API3: Broken Property Auth** | ✅ | `additionalProperties: false` rejects unexpected fields |
| **API4: Resource Consumption** | ✅ | Per-IP, per-phone, per-account rate limiting with progressive delays |
| **API5: Broken Function Auth** | ✅ | Role-based access; admin endpoints require VPN + admin JWT scope |
| **API6: Sensitive Flows** | ✅ | CAPTCHA on registration, OTP cooldown, account lockout |
| **API7: SSRF** | ✅ | No user-controlled URLs; SMS gateway called with validated phone only |
| **API8: Misconfig** | ✅ | Security headers, TLS 1.3, no debug mode in production |
| **API9: Improper Inventory** | ✅ | Versioned endpoints, deprecated routes return 410 |
| **API10: Unsafe Consumption** | ✅ | SMS gateway responses validated; timeouts enforced |
