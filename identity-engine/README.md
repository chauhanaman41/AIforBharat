# Engine 2 — Identity Engine

> AES-256-GCM encrypted PII vault with DPDP compliance.

| Property | Value |
|----------|-------|
| **Port** | 8002 |
| **Folder** | `identity-engine/` |
| **Database Tables** | `identity_vaults` |

## Run

```bash
uvicorn identity-engine.main:app --port 8002 --reload
```

Docs: http://localhost:8002/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/identity/create` | Create encrypted identity vault for user |
| GET | `/identity/{token}` | Retrieve and decrypt identity (auth required) |
| GET | `/identity/{token}/profile` | Minimal non-sensitive profile view |
| PUT | `/identity/{token}/roles` | Update user roles |
| POST | `/identity/{token}/export` | DPDP data export (right to portability) |
| DELETE | `/identity/{token}` | Cryptographic deletion (right to forget) |

## Security

- Each PII field (name, Aadhaar, PAN, address, etc.) is **individually encrypted** with AES-256-GCM
- Unique nonce per encryption operation
- Cryptographic deletion: overwrites encrypted fields with random bytes before deletion
- Data export returns all decrypted fields for the user (DPDP compliance)
- DigiLocker verification: **stubbed** (returns unverified status per design constraint)

## Request Models

- `CreateIdentityRequest` — `user_id`, `full_name`, `aadhaar_number`, `pan_number`, `address`, `date_of_birth`, `gender`, `caste_category`, `state`, `district`, `phone`
- `UpdateRolesRequest` — `roles` (list)

## Events Published

- `IDENTITY_CREATED` — vault created
- `IDENTITY_VERIFIED` — identity retrieved
- `IDENTITY_DELETED` — cryptographic deletion
- `ROLE_UPDATED` — roles changed
- `DATA_EXPORTED` — data export requested

## Gateway Route

`/api/v1/identity/*` → proxied from API Gateway (JWT auth required)

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **User Onboarding** | `POST /api/v1/onboard` | Create encrypted identity vault | Step 2 of 8 |

### Flow Detail: User Onboarding

```
E1 (Register) → E2 (Identity) → E4 (Metadata) → E5 (Processed Meta)
  → E15 ∥ E16 (Eligibility + Deadlines) → E12 (Profile) → E3+E13 (Audit)
```

E2 creates the encrypted PII vault for the newly registered user. Failure here is **non-critical** — the flow continues with degraded identity support.

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/identity/create` during onboarding |
| **Called by** | API Gateway (Proxy) | All `/identity/*` routes for direct access |
| **Called by** | JSON User Info Generator (E12) | Profile assembly — reads identity data |
| **Publishes to** | Event Bus → E3, E13 | `IDENTITY_CREATED`, `IDENTITY_VERIFIED`, `IDENTITY_DELETED`, `ROLE_UPDATED`, `DATA_EXPORTED` |

## Shared Module Dependencies

- `shared/config.py` — `settings` (AES encryption key, port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`
- `shared/event_bus.py` — `event_bus`
- `shared/utils.py` — `generate_id()`
