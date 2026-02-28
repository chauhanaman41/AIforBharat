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
