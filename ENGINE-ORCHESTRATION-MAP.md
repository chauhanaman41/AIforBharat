# AIforBharat — Complete Engine Orchestration Map

> Generated for orchestration layer design. Covers all 21 engines.
> Shared DB: `data/aiforbharat.db` (SQLite via SQLAlchemy async)
> Event Bus: `shared/event_bus.py` — in-memory `LocalEventBus` singleton, pub/sub with wildcard `*` support

---

## Shared Infrastructure

### ENGINE_URLS (shared/config.py)
```
api_gateway        → http://localhost:8000
login_register     → http://localhost:8001
identity           → http://localhost:8002
raw_data_store     → http://localhost:8003
metadata           → http://localhost:8004
processed_metadata → http://localhost:8005
vector_database    → http://localhost:8006
neural_network     → http://localhost:8007
anomaly_detection  → http://localhost:8008
chunks             → http://localhost:8010
policy_fetching    → http://localhost:8011
json_user_info     → http://localhost:8012
analytics_warehouse→ http://localhost:8013
dashboard_bff      → http://localhost:8014
eligibility_rules  → http://localhost:8015
deadline_monitoring→ http://localhost:8016
simulation         → http://localhost:8017
gov_data_sync      → http://localhost:8018
trust_scoring      → http://localhost:8019
speech_interface   → http://localhost:8020
doc_understanding  → http://localhost:8021
```

### EventType Enum (shared/models.py)
```
USER_REGISTERED, LOGIN_SUCCESS, LOGIN_FAILED, TOKEN_REFRESHED,
ACCOUNT_LOCKED, LOGOUT,
IDENTITY_CREATED, IDENTITY_VERIFIED, IDENTITY_DELETED,
ROLE_UPDATED, DATA_EXPORTED,
METADATA_CREATED, METADATA_UPDATED, METADATA_CONFLICT, PROFILE_UPDATED,
POLICY_FETCHED, POLICY_UPDATED, POLICY_AMENDED, POLICY_REPEALED,
DOCUMENT_PROCESSED, DOCUMENT_VERIFIED,
ELIGIBILITY_COMPUTED, ELIGIBILITY_CACHE_INVALIDATED,
DEADLINE_CREATED, DEADLINE_ESCALATED, DEADLINE_COMPLETED,
AI_RESPONSE_GENERATED, ANOMALY_DETECTED, TRUST_SCORE_COMPUTED,
SIMULATION_COMPLETED,
RAW_DATA_STORED, INTEGRITY_VIOLATION, METADATA_STORED,
GOV_DATA_SYNCED, BUDGET_REALLOCATED,
SYSTEM_ERROR, HEALTH_CHECK
```

### Shared DB Tables (shared/database.py)
All engines share a single SQLite DB via `Base.metadata.create_all()` at startup.

---

## Engine 1: API Gateway (port 8000)

### Files: main.py, routes.py, middleware.py

### Routes (all under `/api/v1`)
| Method | Path | Auth | Proxies To |
|--------|------|------|------------|
| GET | `/health` | No | Local |
| GET | `/` | No | Local (service directory) |
| GET/POST/PUT/DELETE | `/api/v1/auth/{path}` | No | login_register :8001 → `/auth/{path}` |
| GET/POST/PUT/DELETE | `/api/v1/identity/{path}` | **Yes** | identity :8002 → `/identity/{path}` |
| GET/POST/PUT | `/api/v1/metadata/{path}` | **Yes** | metadata :8004 → `/metadata/{path}` |
| GET/POST | `/api/v1/eligibility/{path}` | **Yes** | eligibility_rules :8015 → `/eligibility/{path}` |
| GET/POST | `/api/v1/schemes/{path}` | No | policy_fetching :8011 → `/schemes/{path}` |
| GET/POST | `/api/v1/policies/{path}` | No | policy_fetching :8011 → `/policies/{path}` |
| GET/POST | `/api/v1/simulate/{path}` | **Yes** | simulation :8017 → `/simulate/{path}` |
| GET/POST/PUT | `/api/v1/deadlines/{path}` | **Yes** | deadline_monitoring :8016 → `/deadlines/{path}` |
| GET/POST | `/api/v1/ai/{path}` | **Yes** | neural_network :8007 → `/ai/{path}` |
| GET/POST/PUT | `/api/v1/dashboard/{path}` | **Yes** | dashboard_bff :8014 → `/dashboard/{path}` |
| GET/POST | `/api/v1/documents/{path}` | **Yes** | doc_understanding :8021 → `/documents/{path}` |
| GET/POST/PUT | `/api/v1/voice/{path}` | **Yes** | speech_interface :8020 → `/voice/{path}` |
| GET/POST | `/api/v1/analytics/{path}` | **Yes** | analytics_warehouse :8013 → `/analytics/{path}` |
| GET/POST | `/api/v1/trust/{path}` | **Yes** | trust_scoring :8019 → `/trust/{path}` |
| GET/POST | `/api/v1/profile/{path}` | **Yes** | json_user_info :8012 → `/profile/{path}` |
| GET | `/api/v1/debug/events` | **Yes** | Local (event bus history) |

### Event Bus: None (no subscribe/publish)
### HTTP Calls: Proxies ALL requests to downstream engines via `httpx.AsyncClient`
### Startup: `init_db()`
### Middleware: RateLimitMiddleware (100/min per IP), RequestLoggingMiddleware, CORS, TrustedHost, RequestID
### DB Tables: None (stateless proxy)

---

## Engine 2: Login/Register Engine (port 8001)

### Files: main.py, routes.py, models.py

### Routes (prefix `/auth`)
| Method | Path | Auth | Request Body | Response |
|--------|------|------|--------------|----------|
| POST | `/auth/register` | No | `{phone, password, name, state?, district?, language_preference?, consent_data_processing}` | `{user_id, phone, name, access_token, refresh_token}` |
| POST | `/auth/login` | No | `{phone, password}` | `{user_id, name, access_token, refresh_token}` |
| POST | `/auth/otp/send` | No | `{phone, purpose}` | `{otp_id, phone, expires_in_seconds, debug_otp}` |
| POST | `/auth/otp/verify` | No | `{phone, otp_code}` | `{verified, phone}` |
| POST | `/auth/token/refresh` | No | `{refresh_token}` | `{access_token, refresh_token}` |
| POST | `/auth/logout` | **Yes** | — | `{message}` |
| GET | `/auth/me` | **Yes** | — | Full user profile |
| PUT | `/auth/profile` | **Yes** | `{name?, email?, date_of_birth?, gender?, state?, district?, pincode?, language_preference?}` | `{user_id, updated_fields}` |
| GET | `/health` | No | — | HealthResponse |

### Event Bus — Publishes:
| Event Type | When |
|------------|------|
| `USER_REGISTERED` | After successful registration |
| `LOGIN_SUCCESS` | After successful login |
| `LOGIN_FAILED` | After failed login attempt |
| `ACCOUNT_LOCKED` | After 5 failed attempts |
| `TOKEN_REFRESHED` | After token refresh |
| `LOGOUT` | After logout |
| `PROFILE_UPDATED` | After profile update |

### Event Bus — Subscribes: **None**
### HTTP Calls to Other Engines: **None**
### DB Tables: `users`, `otp_records`, `refresh_tokens` (defined in models.py)
### Startup: `init_db()`, imports models

---

## Engine 3: Identity Engine (port 8002)

### Files: main.py, routes.py, models.py

### Routes (prefix `/identity`)
| Method | Path | Auth | Request Body | Response |
|--------|------|------|--------------|----------|
| POST | `/identity/create` | No | `{user_id, name?, phone?, email?, address?, dob?, aadhaar?, pan?}` | `{identity_token, user_id}` |
| GET | `/identity/{token}` | No | — | Decrypted PII fields |
| GET | `/identity/{token}/profile` | No | — | Minimal profile (non-sensitive) |
| PUT | `/identity/{token}/roles` | No | `{roles: [str]}` | `{roles}` |
| POST | `/identity/{token}/export` | No | — | Full data export (DPDP) |
| DELETE | `/identity/{token}` | No | — | Cryptographic deletion |
| GET | `/health` | No | — | HealthResponse |

### Event Bus — Publishes:
| Event Type | When |
|------------|------|
| `IDENTITY_CREATED` | After identity vault created |
| `ROLE_UPDATED` | After roles changed |
| `DATA_EXPORTED` | After data export |
| `IDENTITY_DELETED` | After cryptographic deletion |

### Event Bus — Subscribes: **None**
### HTTP Calls to Other Engines: **None**
### DB Tables: `identity_vault` (AES-256-GCM encrypted PII)
### Startup: `init_db()`

---

## Engine 4: Raw Data Store (port 8003)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/raw-data/events` | `{event_type, source_engine, user_id?, payload}` | `{event_id, hash, timestamp}` |
| GET | `/raw-data/events/{event_id}` | — | Event record |
| GET | `/raw-data/events` | Query: `source_engine?, event_type?, limit` | `{events, count}` |
| GET | `/raw-data/user/{user_id}/trail` | Query: `limit` | User audit trail |
| POST | `/raw-data/integrity/verify` | `{event_ids: [str]}` | Hash chain verification results |
| GET | `/health` | — | HealthResponse |

### Event Bus — Publishes:
| Event Type | When |
|------------|------|
| `RAW_DATA_STORED` | After event stored via POST endpoint |

### Event Bus — Subscribes:
| Pattern | Handler | Purpose |
|---------|---------|---------|
| `*` (wildcard) | `_audit_event_handler` | Stores ALL events from bus as audit records with SHA-256 hash chain |

### HTTP Calls to Other Engines: **None**
### DB Tables: **None** (filesystem-based: `data/raw-store/hot|warm|cold/`)
### Startup: Subscribes to `*` on event bus

---

## Engine 5: Metadata Engine (port 8004)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/metadata/process` | `MetadataProcessRequest` (all user profile fields) | Normalized profile + derived_attributes |
| GET | `/metadata/user/{user_id}` | — | Cached processed metadata |
| POST | `/metadata/validate` | `{fields: dict}` | Per-field validation results |
| GET | `/metadata/schemas` | — | Metadata schema definition |
| GET | `/health` | — | HealthResponse |

**MetadataProcessRequest fields:** `user_id, name?, phone?, email?, date_of_birth?, gender?, state?, district?, pincode?, annual_income?, occupation?, category?, religion?, marital_status?, education_level?, family_size?, is_bpl?, is_rural?, disability_status?, land_holding_acres?, language_preference`

**Derived attributes computed:** `age, age_group, is_minor, is_senior_citizen, income_bracket, tax_bracket, is_bpl, life_stage, employment_category, is_sc_st, is_obc, is_ews, area_type, farmer_category`

### Event Bus — Publishes:
| Event Type | When |
|------------|------|
| `METADATA_CREATED` | After metadata processed |

### Event Bus — Subscribes: **None**
### HTTP Calls to Other Engines: **None**
### DB Tables: **None** (in-memory LocalCache only)
### Startup: `init_db()`

---

## Engine 6: Processed User Metadata Store (port 8005)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/processed-metadata/store` | `{user_id, processed_data, derived_attributes?}` | Confirmation |
| GET | `/processed-metadata/user/{user_id}` | — | Full processed metadata |
| PUT | `/processed-metadata/user/{user_id}` | `{updates: dict}` | Confirmation |
| DELETE | `/processed-metadata/user/{user_id}` | — | DPDP erasure |
| POST | `/processed-metadata/eligibility/cache` | `{user_id, scheme_id, scheme_name, is_eligible, confidence, matched_criteria, unmet_criteria, verdict_reason}` | Confirmation |
| GET | `/processed-metadata/eligibility/{user_id}` | Query: `scheme_id?` | Cached eligibility results |
| POST | `/processed-metadata/risk` | `{user_id, risk_type, risk_score, risk_factors}` | Confirmation |
| GET | `/processed-metadata/risk/{user_id}` | — | Risk scores |
| GET | `/health` | — | HealthResponse |

### Event Bus — Publishes:
| Event Type | When |
|------------|------|
| `METADATA_CREATED` | After metadata stored |

### Event Bus — Subscribes: **None**
### HTTP Calls to Other Engines: **None**
### DB Tables: `user_metadata`, `user_derived_attributes`, `user_eligibility_cache`, `user_risk_scores`
### Startup: `init_db()`

---

## Engine 7: Vector Database (port 8006)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/vectors/upsert` | `{chunk_id?, document_id?, policy_id?, content, embedding?, namespace, metadata}` | `{vector_id, dimensions, index_size}` |
| POST | `/vectors/upsert/batch` | `{vectors: [UpsertVectorRequest]}` | `{inserted, index_size}` |
| POST | `/vectors/search` | `{query, top_k, namespace, min_score, use_embedding}` | Ranked results with scores |
| POST | `/vectors/search/embedding` | `{embedding, top_k, namespace, min_score}` | Ranked results |
| DELETE | `/vectors/{vector_id}` | — | Confirmation |
| DELETE | `/vectors/document/{document_id}` | — | Count deleted |
| GET | `/vectors/stats` | — | `{total_vectors, index_size, embedding_dim, namespaces}` |
| GET | `/health` | — | HealthResponse |

### Event Bus — Publishes: **None**
### Event Bus — Subscribes: **None**
### HTTP Calls: Uses `nvidia_client` for NVIDIA NIM embeddings (external API, not inter-engine)
### DB Tables: `vector_records` (embeddings stored as packed binary)
### In-Memory: `LocalVectorIndex` with cosine similarity search
### Startup: `init_db()`, loads all vectors from DB into memory index

---

## Engine 8: Neural Network Engine (port 8007)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/ai/chat` | `{user_id, session_id?, message, context?, max_tokens, temperature}` | `{response, session_id, latency_ms}` |
| POST | `/ai/rag` | `{user_id, question, context_passages, max_tokens}` | `{answer, context_used, question}` |
| POST | `/ai/intent` | `{message, user_id?}` | `{intent, entities, confidence, language}` |
| POST | `/ai/summarize` | `{text, max_length}` | `{summary, original_length}` |
| POST | `/ai/translate` | `{text, source_lang, target_lang}` | `{original, translated, source_lang, target_lang}` |
| POST | `/ai/embeddings` | `{texts: [str]}` | `{embeddings, dimensions, count}` |
| GET | `/ai/history/{user_id}` | Query: `session_id?, limit` | Conversation history |
| GET | `/health` | — | HealthResponse |

### Event Bus — Publishes:
| Event Type | When | ⚠️ |
|------------|------|----|
| `AI_QUERY_PROCESSED` | After chat response | **NOT in EventType enum — will fail at runtime** |

### Event Bus — Subscribes: **None**
### HTTP Calls: Uses `nvidia_client` for NVIDIA NIM LLM API (external)
### DB Tables: `conversation_logs`
### Startup: `init_db()`

---

## Engine 9: Anomaly Detection Engine (port 8008)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/anomaly/check` | `{user_id, profile: dict}` | `{total_anomalies, aggregate_risk_score, severity_counts, anomalies}` |
| GET | `/anomaly/user/{user_id}` | Query: `status?` | Anomaly records |
| PUT | `/anomaly/{anomaly_id}/resolve` | `{status, notes}` | Confirmation |
| GET | `/anomaly/stats` | — | Counts by type/severity |
| GET | `/health` | — | HealthResponse |

### Event Bus — Publishes:
| Event Type | When |
|------------|------|
| `ANOMALY_DETECTED` | When aggregate risk score > 0.5 |

### Event Bus — Subscribes: **None**
### HTTP Calls to Other Engines: **None**
### DB Tables: `anomaly_records`
### Startup: `init_db()`

---

## Engine 10: Chunks Engine (port 8010)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/chunks/create` | `{document_id, policy_id?, text, strategy, chunk_size, overlap, metadata}` | `{document_id, total_chunks, chunks}` |
| POST | `/chunks/batch` | `{documents: [ChunkRequest]}` | Batch results |
| GET | `/chunks/document/{document_id}` | — | All chunks for document |
| GET | `/chunks/{chunk_id}` | — | Single chunk |
| POST | `/chunks/rechunk` | `{document_id, strategy, chunk_size}` | Re-chunked results |
| GET | `/chunks/stats` | — | `{total_chunks, unique_documents, avg_chunk_size}` |
| GET | `/health` | — | HealthResponse |

**Strategies:** `fixed`, `sentence`, `section`, `paragraph`

### Event Bus — Publishes:
| Event Type | When | ⚠️ |
|------------|------|----|
| `CHUNKS_CREATED` | After chunks created | **NOT in EventType enum** |

### Event Bus — Subscribes:
| Pattern | Handler | Purpose |
|---------|---------|---------|
| `document.*` | `_on_document_event` | Auto-chunk on new documents (handler is a stub — logs only) |

### HTTP Calls to Other Engines: **None**
### DB Tables: `document_chunks`
### Startup: `init_db()`, subscribes to `document.*`

---

## Engine 11: Policy Fetching Engine (port 8011)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/policies/fetch` | `{source_id, url?, document_type, content?, metadata}` | `{change_type, version, content_hash}` |
| GET | `/policies/list` | Query: `source_id?, document_type?, ministry?, limit, offset` | Policy list |
| GET | `/policies/{policy_id}` | — | Full policy with content |
| GET | `/policies/{policy_id}/versions` | — | Version history |
| POST | `/policies/search` | `{query, ministry?, document_type?, limit}` | Search results |
| GET | `/policies/sources/list` | — | Configured sources with health metrics |
| POST | `/policies/sources/add` | `{source_id, name, url, source_type, schedule_cron, rate_limit_per_sec}` | Confirmation |
| GET | `/health` | — | HealthResponse |

### Event Bus — Publishes:
| Event Type | When | ⚠️ |
|------------|------|----|
| `DOCUMENT_FETCHED` | New document fetched | **NOT in EventType enum** |
| `DOCUMENT_UPDATED` | Existing document changed | **NOT in EventType enum** |

### Event Bus — Subscribes: **None**
### HTTP Calls to Other Engines: **None** (uses BackgroundTasks parameter but doesn't schedule any)
### DB Tables: `fetched_documents`, `source_configs`
### Filesystem: `data/policies/` (local document cache)
### Startup: `init_db()`, seeds 5 default sources + 10 pre-loaded schemes

---

## Engine 12: JSON User Info Generator (port 8012)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/profile/generate` | `{user_id, metadata?, eligibility?, trust_score?, anomaly_data?, deadlines?}` | Comprehensive assembled profile |
| GET | `/profile/{user_id}` | — | Latest generated profile |
| GET | `/profile/{user_id}/summary` | — | Compact summary for AI prompts |
| GET | `/health` | — | HealthResponse |

### Event Bus — Publishes:
| Event Type | When | ⚠️ |
|------------|------|----|
| `PROFILE_GENERATED` | After profile assembled | **NOT in EventType enum** |

### Event Bus — Subscribes: **None**
### HTTP Calls to Other Engines: **None** (receives data as input; does NOT call other engines itself)
### DB Tables: `generated_profiles`
### Startup: `init_db()`

---

## Engine 13: Analytics Warehouse (port 8013)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/analytics/events` | `{event_type, user_id?, engine?, payload}` | Confirmation |
| POST | `/analytics/metrics` | `{metric_name, metric_value, dimension, dimension_value}` | Confirmation |
| POST | `/analytics/funnel` | `{funnel_name, step_name, step_order, user_id}` | Confirmation |
| GET | `/analytics/dashboard` | — | Platform summary |
| GET | `/analytics/events/query` | Query: `event_type?, user_id?, engine?, limit` | Event list |
| GET | `/analytics/metrics/query` | Query: `metric_name?, dimension?, limit` | Metric snapshots |
| GET | `/analytics/funnel/{funnel_name}` | — | Funnel analysis with drop-off |
| GET | `/analytics/scheme-popularity` | — | Ranked scheme interactions |
| GET | `/health` | — | HealthResponse |

### Event Bus — Subscribes:
| Pattern | Handler | Purpose | ⚠️ |
|---------|---------|---------|-----|
| `*` (wildcard) | `_on_event` | Counts events, engines, users, schemes | **BUG: handler expects `dict` but receives `EventMessage`** |

### Event Bus — Publishes: **None**
### HTTP Calls to Other Engines: **None**
### DB Tables: `analytics_events`, `metric_snapshots`, `funnel_steps`
### In-Memory: Counters for events, schemes, engines, users
### Startup: `init_db()`, subscribes to `*`

---

## Engine 14: Dashboard Interface / BFF (port 8014)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| GET | `/dashboard/home/{user_id}` | — | Widgets, navigation, quick actions |
| GET | `/dashboard/schemes` | — | Scheme overview (hardcoded list) |
| GET | `/dashboard/engines/status` | — | All 21 engine statuses |
| GET | `/dashboard/preferences/{user_id}` | — | User preferences |
| PUT | `/dashboard/preferences/{user_id}` | `{theme?, language?, widget_order?, notifications_enabled?}` | Confirmation |
| GET | `/dashboard/search` | Query: `q` | Global search results |
| GET | `/health` | — | HealthResponse |

### Event Bus — Subscribes: **None**
### Event Bus — Publishes: **None**
### HTTP Calls to Other Engines: **None** (returns widget URLs; frontend calls engines directly)
### DB Tables: `dashboard_preferences`
### Startup: `init_db()`

---

## Engine 15: Eligibility Rules Engine (port 8015)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/eligibility/check` | `{user_id, profile: dict, scheme_ids?: [str]}` | `{total_schemes_checked, eligible, partial, ineligible, results}` |
| GET | `/eligibility/history/{user_id}` | — | Previous results |
| GET | `/eligibility/rules` | Query: `scheme_id?` | All rules |
| POST | `/eligibility/rules/add` | `{scheme_id, scheme_name, field, operator, value, is_mandatory, description}` | Confirmation |
| GET | `/eligibility/schemes` | — | Schemes with rule counts |
| GET | `/health` | — | HealthResponse |

**Built-in schemes (10):** PM-KISAN, Ayushman Bharat, PM Awas Yojana, PM Ujjwala, MUDRA, PMSBY, PMJJBY, Sukanya Samriddhi, NPS, SC/ST Scholarship

### Event Bus — Publishes:
| Event Type | When | ⚠️ |
|------------|------|----|
| `ELIGIBILITY_CHECKED` | After eligibility evaluation | **NOT in EventType enum** |

### Event Bus — Subscribes: **None**
### HTTP Calls to Other Engines: **None**
### DB Tables: `eligibility_rules`, `eligibility_results`
### Startup: `init_db()`, seeds built-in rules

---

## Engine 16: Deadline Monitoring Engine (port 8016)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/deadlines/check` | `{user_id, scheme_ids?, state?, days_ahead}` | `{total_deadlines, critical, upcoming_7_days, alerts}` |
| GET | `/deadlines/list` | Query: `active_only?, scheme_id?, limit` | All deadlines |
| POST | `/deadlines/add` | `{scheme_id, scheme_name, deadline_type, deadline_date, ...}` | Confirmation |
| GET | `/deadlines/user/{user_id}/history` | — | Alert history |
| GET | `/health` | — | HealthResponse |

### Event Bus — Publishes:
| Event Type | When | ⚠️ |
|------------|------|----|
| `DEADLINE_APPROACHING` | After deadline check | **NOT in EventType enum** |

### Event Bus — Subscribes: **None**
### HTTP Calls to Other Engines: **None**
### DB Tables: `scheme_deadlines`, `user_deadline_alerts`
### Startup: `init_db()`, seeds 5 deadlines

---

## Engine 17: Simulation Engine (port 8017)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/simulate/what-if` | `{user_id, current_profile, changes, scenario_type}` | `{gained, lost, net_benefit_change, recommendations}` |
| POST | `/simulate/life-event` | `{user_id, current_profile, life_event}` | Same as what-if |
| POST | `/simulate/compare` | `{user_id, profile_a, profile_b}` | `{common, only_profile_a, only_profile_b}` |
| GET | `/simulate/history/{user_id}` | — | Simulation history |
| GET | `/health` | — | HealthResponse |

**Life events:** `marriage`, `child_born`, `job_loss`, `retirement`, `relocation`, `promotion`

### Event Bus — Publishes:
| Event Type | When | ⚠️ |
|------------|------|----|
| `SIMULATION_RUN` | After simulation | **NOT in EventType enum** |

### Event Bus — Subscribes: **None**
### HTTP Calls to Other Engines: **None** (self-contained eligibility rules copy)
### DB Tables: `simulation_records`
### Startup: `init_db()`

---

## Engine 18: Government Data Sync Engine (port 8018)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/gov-data/sync` | `{dataset_id, force_refresh}` | Sync status |
| POST | `/gov-data/query` | `{dataset_id, state?, district?, year?, limit}` | `{dataset_id, count, records}` |
| GET | `/gov-data/datasets` | Query: `category?` | All datasets |
| GET | `/gov-data/dataset/{dataset_id}` | — | Dataset details + sample |
| POST | `/gov-data/datasets/add` | `{dataset_id, name, source, category, description, records}` | Confirmation |
| GET | `/health` | — | HealthResponse |

**Seed datasets (5):** NFHS-5 District, Census 2011, SDG India Index, Poverty Headcount, Scheme Beneficiaries

### Event Bus — Subscribes: **None**
### Event Bus — Publishes: **None**
### HTTP Calls to Other Engines: **None** (local-first; real data.gov.in sync is stubbed)
### DB Tables: `synced_datasets`, `gov_data_records`
### Filesystem: `data/gov-data/`
### Startup: `init_db()`, seeds datasets + sample records

---

## Engine 19: Trust Scoring Engine (port 8019)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/trust/compute` | `{user_id, profile, anomaly_data?, behavior_data?}` | `{overall_score, trust_level, components, positive_factors, negative_factors}` |
| GET | `/trust/user/{user_id}` | — | Latest trust score |
| GET | `/trust/user/{user_id}/history` | Query: `limit` | Score history |
| GET | `/health` | — | HealthResponse |

**Trust levels:** UNVERIFIED (<30), LOW (30-50), MEDIUM (50-70), HIGH (70-85), VERIFIED (85+)
**Components (weighted):** data_completeness (30%), anomaly_check (25%), consistency (20%), behavior (15%), verification (10%)

### Event Bus — Publishes:
| Event Type | When | ⚠️ |
|------------|------|----|
| `TRUST_SCORE_UPDATED` | After trust score computed | **NOT in EventType enum** |

### Event Bus — Subscribes: **None**
### HTTP Calls to Other Engines: **None**
### DB Tables: `trust_scores`
### Startup: `init_db()`

---

## Engine 20: Speech Interface Engine (port 8020)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/speech/stt` | File upload: `audio` + Form: `language` | `{transcript, language, confidence}` |
| POST | `/speech/tts` | `{text, language, user_id?}` | `{session_id, audio_available, text, language}` |
| POST | `/speech/query` | `{text, language, user_id?}` | `{session_id, query, response, language, detected_language}` |
| POST | `/speech/detect-language` | `{text}` | `{language, language_code, script_detected}` |
| POST | `/speech/transliterate` | `{text, source_lang, target_lang}` | `{original, transliterated}` |
| GET | `/speech/languages` | — | Supported languages list |
| GET | `/speech/sessions` | Query: `user_id?, limit` | Voice session history |
| GET | `/health` | — | HealthResponse |

**Supported languages:** hindi, english, bengali, tamil, telugu, marathi, gujarati, kannada, malayalam, punjabi, odia, assamese, urdu

### Event Bus — Publishes:
| Event Type | When | ⚠️ |
|------------|------|----|
| `AI_QUERY_PROCESSED` | After voice query processed | **BUG: Uses `source=` instead of `source_engine=` and `data=` instead of `payload=`** |

### Event Bus — Subscribes: **None**
### HTTP Calls: Uses `nvidia_client` for NIM text generation (external); ASR/TTS are stubs
### DB Tables: `voice_sessions`
### Filesystem: `data/audio/`
### Startup: `init_db()`

---

## Engine 21: Document Understanding Engine (port 8021)

### Routes
| Method | Path | Request Body | Response |
|--------|------|--------------|----------|
| POST | `/documents/parse` | `{document_id?, policy_id?, title, text, ministry?, use_nim}` | Structured extraction results |
| POST | `/documents/parse/batch` | `{documents: [ParseDocumentRequest]}` | Batch results |
| GET | `/documents/parsed/{parsed_id}` | — | Previously parsed document |
| GET | `/documents/by-policy/{policy_id}` | — | Parsed documents for policy |
| GET | `/health` | — | HealthResponse |

**Extraction output:** `eligibility_criteria, benefits, required_documents, deadlines, amounts, age_limits, income_limits, target_categories, scheme_type`

### Event Bus — Publishes:
| Event Type | When | ⚠️ |
|------------|------|----|
| `DOCUMENT_PARSED` | After document parsed | **NOT in EventType enum** |

### Event Bus — Subscribes: **None**
### HTTP Calls: Uses `nvidia_client` for NIM LLM extraction (external)
### DB Tables: `parsed_documents`
### Startup: `init_db()`

---

## Summary: Event Bus Topology

### Publishers (who emits what)
```
login_register        → USER_REGISTERED, LOGIN_SUCCESS, LOGIN_FAILED, ACCOUNT_LOCKED,
                         TOKEN_REFRESHED, LOGOUT, PROFILE_UPDATED
identity_engine       → IDENTITY_CREATED, ROLE_UPDATED, DATA_EXPORTED, IDENTITY_DELETED
raw_data_store        → RAW_DATA_STORED
metadata_engine       → METADATA_CREATED
processed_metadata    → METADATA_CREATED
anomaly_detection     → ANOMALY_DETECTED
chunks_engine         → CHUNKS_CREATED ⚠️
policy_fetching       → DOCUMENT_FETCHED ⚠️, DOCUMENT_UPDATED ⚠️
json_user_info        → PROFILE_GENERATED ⚠️
eligibility_rules     → ELIGIBILITY_CHECKED ⚠️
deadline_monitoring   → DEADLINE_APPROACHING ⚠️
simulation_engine     → SIMULATION_RUN ⚠️
trust_scoring         → TRUST_SCORE_UPDATED ⚠️
neural_network        → AI_QUERY_PROCESSED ⚠️
speech_interface      → AI_QUERY_PROCESSED ⚠️ (with wrong field names)
doc_understanding     → DOCUMENT_PARSED ⚠️
```

### Subscribers (who listens to what)
```
raw_data_store        → * (wildcard — captures ALL events for audit trail)
analytics_warehouse   → * (wildcard — counts all events for analytics) ⚠️ handler bug
chunks_engine         → document.* (stub handler, logs only)
```

### ⚠️ EventType Enum Gaps
These event type strings are used in `event_bus.publish()` but are **NOT defined** in the `EventType` enum in `shared/models.py`:
- `AI_QUERY_PROCESSED`
- `CHUNKS_CREATED`
- `DOCUMENT_FETCHED`
- `DOCUMENT_UPDATED`
- `PROFILE_GENERATED`
- `ELIGIBILITY_CHECKED`
- `DEADLINE_APPROACHING`
- `SIMULATION_RUN`
- `TRUST_SCORE_UPDATED`
- `DOCUMENT_PARSED`

These will cause **`ValueError` at runtime** when constructing `EventMessage(event_type=EventType.XXX)`.

---

## Summary: Inter-Engine HTTP Call Map

### Direct HTTP calls between engines: **NONE**
All inter-engine HTTP communication is routed through the **API Gateway** (port 8000) acting as a reverse proxy. Individual engines do NOT call each other directly via HTTP.

### API Gateway Proxy Map
```
/api/v1/auth/*         →  login_register     :8001  /auth/*
/api/v1/identity/*     →  identity            :8002  /identity/*
/api/v1/metadata/*     →  metadata            :8004  /metadata/*
/api/v1/eligibility/*  →  eligibility_rules   :8015  /eligibility/*
/api/v1/schemes/*      →  policy_fetching     :8011  /schemes/*
/api/v1/policies/*     →  policy_fetching     :8011  /policies/*
/api/v1/simulate/*     →  simulation          :8017  /simulate/*
/api/v1/deadlines/*    →  deadline_monitoring :8016  /deadlines/*
/api/v1/ai/*           →  neural_network      :8007  /ai/*
/api/v1/dashboard/*    →  dashboard_bff       :8014  /dashboard/*
/api/v1/documents/*    →  doc_understanding   :8021  /documents/*
/api/v1/voice/*        →  speech_interface    :8020  /voice/*
/api/v1/analytics/*    →  analytics_warehouse :8013  /analytics/*
/api/v1/trust/*        →  trust_scoring       :8019  /trust/*
/api/v1/profile/*      →  json_user_info      :8012  /profile/*
```

**Not proxied (no gateway routes):**
- raw_data_store :8003
- processed_metadata :8005
- vector_database :8006
- anomaly_detection :8008
- chunks :8010

---

## Summary: Database Tables by Engine

| Engine | Tables |
|--------|--------|
| Login/Register (8001) | `users`, `otp_records`, `refresh_tokens` |
| Identity (8002) | `identity_vault` |
| Raw Data Store (8003) | *(filesystem only)* |
| Metadata (8004) | *(cache only)* |
| Processed Metadata (8005) | `user_metadata`, `user_derived_attributes`, `user_eligibility_cache`, `user_risk_scores` |
| Vector Database (8006) | `vector_records` |
| Neural Network (8007) | `conversation_logs` |
| Anomaly Detection (8008) | `anomaly_records` |
| Chunks (8010) | `document_chunks` |
| Policy Fetching (8011) | `fetched_documents`, `source_configs` |
| JSON User Info (8012) | `generated_profiles` |
| Analytics Warehouse (8013) | `analytics_events`, `metric_snapshots`, `funnel_steps` |
| Dashboard (8014) | `dashboard_preferences` |
| Eligibility Rules (8015) | `eligibility_rules`, `eligibility_results` |
| Deadline Monitoring (8016) | `scheme_deadlines`, `user_deadline_alerts` |
| Simulation (8017) | `simulation_records` |
| Gov Data Sync (8018) | `synced_datasets`, `gov_data_records` |
| Trust Scoring (8019) | `trust_scores` |
| Speech Interface (8020) | `voice_sessions` |
| Document Understanding (8021) | `parsed_documents` |
| **API Gateway (8000)** | *(none — stateless proxy)* |

> All tables live in a **single shared SQLite DB**: `data/aiforbharat.db`

---

## Summary: Startup / Lifespan Logic

Every engine uses `@asynccontextmanager async def lifespan(app)` with `init_db()` (creates all tables).

Additional startup actions:
| Engine | Extra Startup |
|--------|---------------|
| Raw Data Store (8003) | `event_bus.subscribe("*", _audit_event_handler)` |
| Chunks (8010) | `event_bus.subscribe("document.*", _on_document_event)` |
| Policy Fetching (8011) | Seeds 5 sources + 10 schemes |
| Analytics Warehouse (8013) | `event_bus.subscribe("*", _on_event)` |
| Eligibility Rules (8015) | Seeds 10 schemes × rules |
| Deadline Monitoring (8016) | Seeds 5 deadlines |
| Gov Data Sync (8018) | Seeds 5 datasets + sample records |
| Vector Database (8006) | Loads all vectors from DB into in-memory index |

---

## Background Tasks / Scheduled Jobs

**None of the engines implement scheduled jobs or background tasks** (no APScheduler, no cron, no background workers). The `policy-fetching-engine` accepts `BackgroundTasks` as parameter but never schedules any.

---

## Key Orchestration Gaps (for your design)

1. **No engine-to-engine data pipeline**: Each engine is isolated. The orchestrator must chain:
   - Register → Identity create → Metadata process → Processed metadata store → Anomaly check → Trust score → Eligibility check → JSON profile → Deadline check
2. **Policy pipeline missing**: Policy fetch → Document understand → Chunk → Vector upsert (no automation)
3. **Event bus is in-memory singleton**: Events only flow if engines share the same Python process. In multi-process deployment, the event bus is useless.
4. **10 undefined EventTypes**: Will crash at runtime (see above).
5. **Analytics handler bug**: Expects `dict`, receives `EventMessage`.
6. **Speech publish bug**: Wrong field names in `EventMessage` constructor.
7. **5 engines have no gateway route**: raw_data_store, processed_metadata, vector_database, anomaly_detection, chunks — only accessible directly.
