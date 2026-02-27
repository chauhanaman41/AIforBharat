# 🟦 Identity Engine — Design & Plan

## 1. Purpose

The Identity Engine is the **secure identity vault** of the AIforBharat platform. It manages tokenized identities, encrypted user data, zero-knowledge data sharing, and multi-role user management. This engine ensures that user identity is protected, portable, and compliant with Indian data protection regulations (DPDP Act 2023).

It is the **single source of truth** for "who is this user?" across the entire system.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Tokenized Identity** | Each user gets a platform-unique identity token decoupled from PII |
| **Secure Identity Vault** | AES-256 encrypted storage of PII with key rotation |
| **Zero-Knowledge Sharing** | Share eligibility proofs without revealing raw data |
| **Multi-Role Users** | Citizens, farmers, business owners, legal guardians |
| **Delegation Support** | Parent managing child's profile, legal guardian mode |
| **Business Entity Mode** | MSME/startup identity with GSTIN linking |
| **Encryption & Anonymization** | Field-level encryption, anonymized analytics exports |
| **Identity Linking** | Link Aadhaar, PAN, DigiLocker, bank accounts (future) |
| **Data Portability** | User-controlled data export (JSON/PDF) |
| **Right to Forget** | Cryptographic deletion — destroy encryption keys |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Login/Register Engine                      │
│              (Delegates identity ops post-auth)              │
└─────────────────────────┬───────────────────────────────────┘
                          │ EVENT: USER_REGISTERED
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      Identity Engine                         │
│                                                             │
│  ┌──────────────────┐  ┌───────────────────────────────┐    │
│  │  Identity Token  │  │  Identity Vault                │    │
│  │  Generator       │  │                               │    │
│  │                  │  │  ┌───────────────────────┐    │    │
│  │  • UUID v4       │  │  │ Encrypted PII Store   │    │    │
│  │  • Deterministic │  │  │ (AES-256-GCM)         │    │    │
│  │    token from    │  │  │                       │    │    │
│  │    user_id       │  │  │ • Name (enc)          │    │    │
│  └──────────────────┘  │  │ • Phone (enc)         │    │    │
│                        │  │ • Aadhaar hash        │    │    │
│  ┌──────────────────┐  │  │ • PAN hash            │    │    │
│  │  Role Manager    │  │  │ • Address (enc)       │    │    │
│  │                  │  │  └───────────────────────┘    │    │
│  │  • Citizen       │  │                               │    │
│  │  • Farmer        │  │  ┌───────────────────────┐    │    │
│  │  • Business      │  │  │ Delegation Registry   │    │    │
│  │  • Guardian      │  │  │                       │    │    │
│  │  • Admin         │  │  │ • Parent → Child      │    │    │
│  └──────────────────┘  │  │ • Guardian → Ward     │    │    │
│                        │  │ • Business → Owner    │    │    │
│  ┌──────────────────┐  │  └───────────────────────┘    │    │
│  │  ZK Proof Engine │  └───────────────────────────────┘    │
│  │                  │                                       │
│  │  • Age > 60?     │  ┌───────────────────────────────┐    │
│  │  • Income < X?   │  │  Key Management Service       │    │
│  │  • State = Y?    │  │                               │    │
│  │  (without        │  │  • HSM integration            │    │
│  │   revealing      │  │  • Key rotation (90 days)     │    │
│  │   actual data)   │  │  • Per-user encryption keys   │    │
│  └──────────────────┘  └───────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌──────────────┐  ┌────────────┐  ┌──────────────┐
│ PostgreSQL   │  │ Redis      │  │ HSM / KMS    │
│ (Identity    │  │ (Session   │  │ (AWS Cloud   │
│  Vault)      │  │  Cache)    │  │  HSM / NVIDIA│
│              │  │            │  │  Confidential│
│              │  │            │  │  Computing)  │
└──────────────┘  └────────────┘  └──────────────┘
```

### 3.2 Stateless Validation

- Identity validation is **stateless** — JWT contains role + identity token
- Redis caches **active session metadata** (last activity, device info)
- Encryption keys stored in **HSM** — never in application memory long-term
- All PII access requires **audit trail entry** before decryption

---

## 4. Data Models

### 4.1 Identity Record

```json
{
  "identity_token": "idt_a1b2c3d4e5f6",
  "user_id": "usr_uuid_v4",
  "roles": ["citizen", "farmer"],
  "primary_role": "farmer",
  "state": "UP",
  "district": "Lucknow",
  "created_at": "2026-02-26T10:00:00Z",
  "last_verified": "2026-02-26T10:00:00Z",
  "verification_level": "phone_verified",
  "delegations": [
    {
      "type": "parent_child",
      "delegator_id": "usr_parent_uuid",
      "delegatee_id": "usr_child_uuid",
      "permissions": ["read:schemes", "apply:schemes"],
      "expires_at": "2028-02-26T00:00:00Z"
    }
  ]
}
```

### 4.2 Encrypted PII Vault Schema

```sql
CREATE TABLE identity_vault (
    identity_token    VARCHAR(64) PRIMARY KEY,
    user_id           UUID NOT NULL UNIQUE,
    name_enc          BYTEA NOT NULL,          -- AES-256-GCM encrypted
    phone_enc         BYTEA NOT NULL,          -- AES-256-GCM encrypted
    email_enc         BYTEA,                   -- AES-256-GCM encrypted
    aadhaar_hash      VARCHAR(64),             -- SHA-256 hash (not reversible)
    pan_hash          VARCHAR(64),             -- SHA-256 hash (not reversible)
    address_enc       BYTEA,                   -- AES-256-GCM encrypted
    state             VARCHAR(4) NOT NULL,     -- Unencrypted for partitioning
    encryption_key_id VARCHAR(64) NOT NULL,    -- Reference to KMS key
    created_at        TIMESTAMP NOT NULL,
    updated_at        TIMESTAMP NOT NULL,
    is_deleted        BOOLEAN DEFAULT FALSE    -- Soft delete for right-to-forget
);
```

### 4.3 Zero-Knowledge Proof Request/Response

```json
// Request: "Is user eligible for senior citizen scheme?"
{
  "proof_request": {
    "identity_token": "idt_a1b2c3d4e5f6",
    "claims": [
      {"attribute": "age", "operator": ">=", "value": 60},
      {"attribute": "income_annual", "operator": "<=", "value": 500000},
      {"attribute": "state", "operator": "==", "value": "UP"}
    ]
  }
}

// Response: No raw data exposed
{
  "proof_response": {
    "identity_token": "idt_a1b2c3d4e5f6",
    "results": [
      {"claim": "age >= 60", "satisfied": true},
      {"claim": "income_annual <= 500000", "satisfied": true},
      {"claim": "state == UP", "satisfied": true}
    ],
    "all_satisfied": true,
    "proof_hash": "sha256_of_proof",
    "timestamp": "2026-02-26T10:05:00Z"
  }
}
```

---

## 5. Context Flow

```
USER_REGISTERED event received from Event Bus
    │
    ├─► Generate unique identity_token
    ├─► Assign initial role (citizen)
    ├─► Request encryption key from KMS/HSM
    ├─► Encrypt PII fields (name, phone, address)
    ├─► Hash immutable identifiers (Aadhaar, PAN)
    ├─► Store identity record in PostgreSQL
    ├─► Cache session metadata in Redis
    ├─► Publish IDENTITY_CREATED event to Event Bus
    └─► Return identity_token to Login/Register Engine

Subsequently:
    │
    ├─► [Role Update] → Validate eligibility → Update roles → Log change
    ├─► [Delegation Request] → Verify both parties → Create delegation entry
    ├─► [ZK Proof Request] → Decrypt required fields → Compute proofs → Return boolean results
    ├─► [Data Export] → Decrypt all fields → Package as JSON/PDF → Return to user
    └─► [Right to Forget] → Destroy encryption key → Mark record as deleted
```

---

## 6. Event Bus Integration

| Event | Payload | Consumers |
|---|---|---|
| `IDENTITY_CREATED` | `{identity_token, user_id, roles, state}` | Metadata Engine, Analytics |
| `ROLE_UPDATED` | `{identity_token, old_roles, new_roles}` | Eligibility Rules Engine |
| `DELEGATION_CREATED` | `{delegator, delegatee, permissions}` | Audit, Raw Data Store |
| `IDENTITY_VERIFIED` | `{identity_token, verification_level}` | Trust Scoring Engine |
| `DATA_EXPORTED` | `{identity_token, export_type, timestamp}` | Raw Data Store |
| `IDENTITY_DELETED` | `{identity_token, deletion_type}` | All engines (cascade cleanup) |

---

## 7. NVIDIA Stack Alignment

| Component | NVIDIA Tool | Usage |
|---|---|---|
| Encryption at scale | NVIDIA Confidential Computing | GPU-accelerated encryption/decryption |
| Anomaly detection | NVIDIA Morpheus | Monitor identity access patterns |
| Future: Biometric verification | NVIDIA DeepStream + Riva | Face/voice identity verification |
| ZK computation | CUDA-accelerated cryptography | High-throughput zero-knowledge proofs |

---

## 8. Scaling Strategy

| Scale Tier | Users | Strategy |
|---|---|---|
| **Tier 1** (MVP) | < 10K | Single PostgreSQL, local KMS |
| **Tier 2** | 10K – 1M | PostgreSQL with row-level encryption, Redis Sentinel |
| **Tier 3** | 1M – 10M | Sharded PostgreSQL (by region), HSM cluster, key caching |
| **Tier 4** | 10M+ | Multi-region identity vaults, regional HSMs, edge validation |

### Key Decisions

- **Shard key**: `state` (region) — aligns with Indian administrative boundaries
- **Redis Cluster**: Session cache with 30-minute TTL
- **HSM**: AWS CloudHSM or Azure Dedicated HSM for production key management
- **Read replicas**: For ZK proof lookups and role validation (no PII decryption on replicas)

---

## 9. Privacy & Compliance

| Requirement | Implementation |
|---|---|
| **DPDP Act 2023** | Consent-based data collection, purpose limitation |
| **Data Minimization** | Store only what's needed; hash what you can |
| **Right to Forget** | Cryptographic erasure — destroy encryption keys |
| **Data Portability** | Export all user data as structured JSON |
| **Audit Trail** | Every PII access logged with accessor, purpose, timestamp |
| **Consent Management** | Granular consent tracking per data category |
| **Cross-Border** | Data residency in India (no cross-border transfer) |

---

## 10. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/identity/{token}` | Get identity metadata (no PII) |
| `GET` | `/api/v1/identity/{token}/profile` | Get decrypted profile (auth required) |
| `PUT` | `/api/v1/identity/{token}/roles` | Update user roles |
| `POST` | `/api/v1/identity/{token}/delegation` | Create delegation |
| `DELETE` | `/api/v1/identity/{token}/delegation/{id}` | Revoke delegation |
| `POST` | `/api/v1/identity/{token}/verify` | ZK proof verification |
| `POST` | `/api/v1/identity/{token}/export` | Export all user data |
| `DELETE` | `/api/v1/identity/{token}` | Right to forget (cryptographic deletion) |

---

## 11. Dependencies

| Dependency | Direction | Purpose |
|---|---|---|
| **Login/Register Engine** | Upstream | Receives identity creation requests |
| **Metadata Engine** | Downstream | Provides identity context for profile enrichment |
| **Eligibility Rules Engine** | Downstream | ZK proofs for eligibility checks |
| **Trust Scoring Engine** | Downstream | Verification level signals |
| **Raw Data Store** | Downstream | Audit trail for all identity operations |
| **Event Bus** | Bidirectional | Publishes identity events, consumes auth events |
| **KMS/HSM** | External | Encryption key management |

---

## 12. Technology Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11 (FastAPI) |
| Encryption | AES-256-GCM, RSA-2048 for key wrapping |
| Hashing | SHA-256 (Aadhaar/PAN), bcrypt (passwords) |
| Key Management | AWS CloudHSM / HashiCorp Vault |
| Identity Store | PostgreSQL 16 (row-level encryption) |
| Session Cache | Redis 7.x |
| Event Bus | Apache Kafka / NATS |
| ZK Proofs | Custom implementation on CUDA (future) |
| Containerization | Docker + Kubernetes |

---

## 13. Implementation Phases

| Phase | Milestone | Timeline |
|---|---|---|
| **Phase 1** | Identity token generation, role management | Week 1-2 |
| **Phase 2** | Encrypted PII vault, KMS integration | Week 3-4 |
| **Phase 3** | Delegation support, multi-role management | Week 5-6 |
| **Phase 4** | Zero-knowledge proofs (basic boolean claims) | Week 7-8 |
| **Phase 5** | Data export, right-to-forget implementation | Week 9-10 |
| **Phase 6** | Aadhaar/PAN hash linking, DigiLocker integration | Week 12-16 |

---

## 14. Success Metrics

| Metric | Target |
|---|---|
| Identity creation latency (P95) | < 100ms |
| ZK proof computation latency (P95) | < 50ms |
| PII decryption latency (P95) | < 30ms |
| Key rotation success rate | 100% |
| Data export completion rate | > 99.5% |
| Cryptographic deletion verification | 100% audit pass |

---

## 15. Identity & Authentication References (MVP)

| Service | URL | Purpose |
|---|---|---|
| **Aadhaar (UIDAI)** | https://uidai.gov.in | Public stats only — full Aadhaar integration requires government approval |
| **DigiLocker** | https://www.digilocker.gov.in | Verified document pulling for eligibility checks |
| **DigiLocker Developer API** | https://developer.digilocker.gov.in | API documentation for document verification integration |
| **UMANG** | https://web.umang.gov.in | Unified Mobile Application — integration info and reference architecture |

> ⚠️ **Important:** Full Aadhaar eKYC integration requires UIDAI licensing approval from the Government of India. MVP phase uses public stats and hashed references only.

---

## 16. Security Hardening

### 16.1 Rate Limiting

<!-- SECURITY: Identity endpoints handle sensitive PII — rate limits prevent
     data scraping, brute-force token enumeration, and abuse of ZK proof APIs.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  # SECURITY: Identity retrieval — prevent enumeration attacks
  "/api/v1/identity/{token}":
    per_user:
      requests_per_minute: 30
      burst: 5
    per_ip:
      requests_per_minute: 20
      burst: 5

  # SECURITY: Profile decryption is expensive — limit strictly
  "/api/v1/identity/{token}/profile":
    per_user:
      requests_per_minute: 10
      burst: 3

  # SECURITY: ZK proof — compute-intensive, limit abuse
  "/api/v1/identity/{token}/verify":
    per_user:
      requests_per_minute: 15
      burst: 5

  # SECURITY: Data export — very expensive, strict limits
  "/api/v1/identity/{token}/export":
    per_user:
      requests_per_hour: 3
      requests_per_day: 5
      burst: 1

  # SECURITY: Deletion — irreversible, strict limits
  "DELETE /api/v1/identity/{token}":
    per_user:
      requests_per_day: 1
      require_confirmation: true  # Double confirmation required

  # SECURITY: Role updates — admin-only, rate limited
  "/api/v1/identity/{token}/roles":
    per_user:
      requests_per_minute: 5

  rate_limit_response:
    status: 429
    headers:
      Retry-After: "<seconds>"
      X-RateLimit-Limit: "<limit>"
      X-RateLimit-Remaining: "<remaining>"
    body:
      error: "rate_limit_exceeded"
      message: "Too many requests to identity service. Please retry later."
```

### 16.2 Input Validation & Sanitization

<!-- SECURITY: Identity tokens, role updates, and delegation requests
     are strictly validated to prevent injection and authorization bypass.
     OWASP Reference: API3:2023, API8:2023 -->

```python
# SECURITY: Identity token format — strict pattern prevents injection
IDENTITY_TOKEN_SCHEMA = {
    "type": "string",
    "pattern": "^idt_[a-zA-Z0-9]{12,32}$",  # Alphanumeric, fixed prefix
    "description": "Identity tokens must match idt_ prefix + 12-32 alphanumeric chars"
}

# SECURITY: Role update request — enum-only values, no arbitrary strings
ROLE_UPDATE_SCHEMA = {
    "type": "object",
    "required": ["roles"],
    "additionalProperties": False,
    "properties": {
        "roles": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["citizen", "farmer", "business", "guardian", "admin"]
            },
            "minItems": 1,
            "maxItems": 5,
            "uniqueItems": True
        }
    }
}

# SECURITY: Delegation request — strict validation
DELEGATION_SCHEMA = {
    "type": "object",
    "required": ["delegatee_token", "permissions", "type"],
    "additionalProperties": False,
    "properties": {
        "delegatee_token": {
            "type": "string",
            "pattern": "^idt_[a-zA-Z0-9]{12,32}$"
        },
        "type": {
            "type": "string",
            "enum": ["parent_child", "guardian_ward", "business_owner"]
        },
        "permissions": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["read:schemes", "apply:schemes", "read:profile", "update:profile"]
            },
            "minItems": 1,
            "maxItems": 10
        },
        "expires_at": {
            "type": "string",
            "format": "date-time"
        }
    }
}

# SECURITY: ZK Proof request — prevent arbitrary attribute access
ZK_PROOF_SCHEMA = {
    "type": "object",
    "required": ["claims"],
    "additionalProperties": False,
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["attribute", "operator", "value"],
                "additionalProperties": False,
                "properties": {
                    "attribute": {
                        "type": "string",
                        "enum": ["age", "income_annual", "state", "gender", "bpl_status",
                                 "land_holding", "marital_status", "dependents_count"]
                    },
                    "operator": {
                        "type": "string",
                        "enum": ["==", "!=", ">=", "<=", ">", "<"]
                    },
                    "value": {
                        "oneOf": [
                            {"type": "number"},
                            {"type": "string", "maxLength": 64},
                            {"type": "boolean"}
                        ]
                    }
                }
            },
            "minItems": 1,
            "maxItems": 10  # Prevent DoS via excessive claims
        }
    }
}
```

### 16.3 Secure API Key & Secret Management

<!-- SECURITY: Encryption keys for PII vault are managed exclusively
     via HSM/KMS — never in application code or config files.
     OWASP Reference: API1:2023 -->

```yaml
secrets_management:
  environment_variables:
    - KMS_ENDPOINT              # HSM/KMS service endpoint
    - KMS_ACCESS_KEY_ID         # KMS authentication
    - KMS_SECRET_ACCESS_KEY     # KMS authentication (rotated)
    - DB_PASSWORD               # PostgreSQL identity vault password
    - REDIS_PASSWORD            # Session cache password
    - KAFKA_SASL_PASSWORD       # Event bus auth
    - MASTER_ENCRYPTION_KEY_ID  # KMS key ID for PII encryption

  # SECURITY: Per-user encryption keys stored in HSM, never in app memory long-term
  key_management:
    provider: aws_cloudhsm  # Or HashiCorp Vault Transit
    key_rotation: 90_days
    key_wrapping: RSA-2048  # Master key wraps per-user AES-256 keys
    key_cache_ttl: 300      # Cache decrypted keys for 5 min max
    audit_every_access: true  # Log every key retrieval with accessor + purpose

  # SECURITY: No PII or encryption keys in logs, responses, or error messages
  redaction:
    - fields: ["name_enc", "phone_enc", "email_enc", "address_enc"]
      action: "never_log"
    - fields: ["aadhaar_hash", "pan_hash"]
      action: "mask_in_logs"  # Show first 4 chars only
```

### 16.4 OWASP Compliance

| OWASP Risk | Mitigation |
|---|---|
| **API1: BOLA** | Identity token ownership verified via JWT `sub`; delegation checked for cross-user access |
| **API2: Broken Auth** | PII decryption requires valid JWT + audit trail entry |
| **API3: Broken Property Auth** | `additionalProperties: false` on all schemas; ZK proofs hide raw data |
| **API4: Resource Consumption** | Compute-heavy ZK proofs and data exports rate-limited strictly |
| **API5: Broken Function Auth** | Role updates restricted to admin; delegation requires both-party consent |
| **API6: Sensitive Flows** | Data export and deletion require re-authentication + confirmation |
| **API7: SSRF** | No external URLs accepted in identity operations |
| **API8: Misconfig** | AES-256-GCM encryption, TLS 1.3, no debug endpoints in production |
| **API9: Improper Inventory** | Versioned identity schemas with migration support |
| **API10: Unsafe Consumption** | KMS/HSM responses validated; timeout on all external calls |

---

## ⚙️ Build Phase Instructions (Current Phase Override)

> **These instructions override any conflicting guidance above for the current local build phase.**

### 1. Local-First Architecture
- Build and run this engine **entirely locally**. Do NOT integrate any AWS cloud services (AWS CloudHSM, Azure Dedicated HSM, AWS KMS, etc.).
- Use **local encryption** (Python `cryptography` library with AES-256-GCM) instead of cloud HSM/KMS.
- Store encryption keys in a local `.env` file or local key file (not cloud vaults).
- All references to cloud infrastructure are deferred to the cloud migration phase.

### 2. Data Storage & Caching (Zero-Redundancy)
- Before downloading or fetching any external data/files, **always check if the target data already exists locally**.
- If present locally → skip the download and load directly from the local path.
- Only download/fetch data if it is **completely missing locally**.
- Use local PostgreSQL for the identity vault.

### 3. Deferred Features (Do NOT Implement Yet)
- **DigiLocker Verification**: Skip entirely. Do not implement DigiLocker identity linking, OAuth2 flows, or document pulls from `developer.digilocker.gov.in`.
- **Aadhaar/UIDAI Integration**: Skip entirely. No eKYC or UIDAI API calls.
- **UMANG Integration**: Skip entirely.
- **Notifications & Messaging**: Do not build or integrate any notification systems (SMS, email, push, etc.).
- **Cloud HSM/KMS**: Use local encryption libraries instead.

### 4. Primary Focus
Build a robust, locally-functioning identity vault with:
- Tokenized identity storage (local AES-256-GCM encryption)
- Zero-knowledge proof infrastructure (local computation)
- Identity CRUD operations
- Audit trail logging (local)
- All functionality testable without any external service or cloud dependencies
