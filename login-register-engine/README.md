# Engine 1 — Login & Register Engine

> User authentication and session management for AIforBharat.

| Property | Value |
|----------|-------|
| **Port** | 8001 |
| **Folder** | `login-register-engine/` |
| **Database Tables** | `users`, `otp_records`, `refresh_tokens` |

## Run

```bash
uvicorn login-register-engine.main:app --port 8001 --reload
```

Docs: http://localhost:8001/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/auth/register` | Register new user (phone + password) |
| POST | `/auth/login` | Login → JWT access + refresh tokens |
| POST | `/auth/otp/send` | Send OTP (logged to console, not SMS) |
| POST | `/auth/otp/verify` | Verify OTP code |
| POST | `/auth/token/refresh` | Refresh expired access token |
| POST | `/auth/logout` | Invalidate session |
| GET | `/auth/me` | Get current user profile (JWT required) |
| PUT | `/auth/profile` | Update user profile fields |

## Request / Response Models

- `RegisterRequest` — `phone`, `password`, `full_name`, `roles`
- `LoginRequest` — `phone`, `password`
- `OTPSendRequest` — `phone`
- `OTPVerifyRequest` — `phone`, `otp`
- `TokenRefreshRequest` — `refresh_token`
- `ProfileUpdateRequest` — optional `full_name`, `email`, `preferred_language`

## Auth Details

- Passwords hashed with **bcrypt** (12 rounds)
- JWT signed with **HS256** (secret from `shared/config.py`)
- Access token: 30 min expiry
- Refresh token: 7 day expiry
- OTP: 6-digit, logged to console (no SMS integration per design constraints)

## Events Published

- `USER_REGISTERED` — on successful registration
- `LOGIN_SUCCESS` — on successful login
- `LOGIN_FAILED` — on failed login attempt
- `TOKEN_REFRESHED` — on token refresh
- `LOGOUT` — on logout

## Gateway Route

`/api/v1/auth/*` → proxied from API Gateway (no auth required)

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **User Onboarding** | `POST /api/v1/onboard` | Register new user (critical first step) | Step 1 of 8 |

### Flow Detail: User Onboarding

```
→ E1 (Register) → E2 (Identity) → E4 (Metadata) → E5 (Processed Meta)
  → E15 ∥ E16 (Eligibility + Deadlines) → E12 (Profile) → E3+E13 (Audit)
```

E1 is the **critical entry point** — if registration fails, the entire onboarding flow aborts (HTTP 500). All subsequent steps degrade gracefully.

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/auth/register` during onboarding |
| **Called by** | API Gateway (Proxy) | All `/auth/*` routes for direct access |
| **Publishes to** | Event Bus → E3, E13 | `USER_REGISTERED`, `LOGIN_SUCCESS`, `LOGIN_FAILED`, `TOKEN_REFRESHED`, `LOGOUT` |

## Shared Module Dependencies

- `shared/config.py` — `settings` (JWT secret, algorithm, token TTLs, port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`
- `shared/event_bus.py` — `event_bus`
- `shared/utils.py` — `generate_id()`, `create_access_token()`
