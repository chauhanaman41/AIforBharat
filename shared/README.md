# Shared Foundation

> Cross-cutting modules imported by all 21 engines.

## Modules

| File | Purpose | Key Exports |
|------|---------|-------------|
| `config.py` | Central configuration | `settings`, `ENGINE_URLS`, `get_engine_url()` |
| `models.py` | Pydantic models & enums | `ApiResponse`, `EventType`, `UserRole`, `EligibilityVerdict`, `TrustLevel` |
| `database.py` | SQLAlchemy async setup | `Base`, `AsyncSessionLocal`, `init_db()`, `get_async_session()` |
| `event_bus.py` | In-memory pub/sub | `event_bus`, `LocalEventBus` |
| `cache.py` | Two-tier L1/L2 cache | `LocalCache`, `file_exists_locally()`, `get_cached_download()` |
| `nvidia_client.py` | NVIDIA NIM wrapper | `nvidia_client`, `NVIDIAClient` |
| `utils.py` | Helpers | `generate_id()`, `create_access_token()`, `INDIAN_STATES`, `format_indian_currency()` |

---

## config.py

Central settings singleton using `pydantic-settings`. All engines read from this.

### Key Settings

| Setting | Value |
|---------|-------|
| Engine ports | 8000–8021 (port 8009 unused) |
| Database | `sqlite+aiosqlite:///data/aiforbharat.db` |
| NVIDIA NIM base URL | `https://integrate.api.nvidia.com/v1` |
| LLM model | `meta/llama-3.1-70b-instruct` |
| Embedding model | `nvidia/nv-embedqa-e5-v5` |
| JWT algorithm | HS256 |
| JWT access token TTL | 30 minutes |
| JWT refresh token TTL | 7 days |
| Rate limit | 100 req/min per IP |
| CORS origins | localhost:5173, :3000, :8000 |

Settings can be overridden via environment variables or a `.env` file in the project root.

---

## models.py

### Enums

- `UserRole` — citizen, farmer, business, guardian, admin
- `EventType` — 30+ event types across auth, identity, policy, AI, data domains
- `EligibilityVerdict` — ELIGIBLE, PARTIAL_MATCH, NOT_ELIGIBLE
- `DeadlinePriority` — info, important, urgent, critical, overdue
- `TrustLevel` — low, medium, high
- `AnomalyScore` — pass, review, block

### Models

- `ApiResponse` — standard wrapper: `success`, `message`, `data`, `errors`
- `HealthResponse` — engine health: `engine`, `status`, `uptime_seconds`
- `EventMessage` — event bus message: `event_type`, `source`, `data`, `timestamp`

---

## database.py

SQLAlchemy 2.0 async setup with SQLite (WAL mode for concurrent reads).

```python
from shared.database import Base, AsyncSessionLocal, init_db

# In engine startup
await init_db()  # Creates all tables

# In endpoint
async with AsyncSessionLocal() as session:
    result = await session.execute(select(MyModel))
```

---

## event_bus.py

In-memory async pub/sub replacing Apache Kafka.

```python
from shared.event_bus import event_bus

# Subscribe
event_bus.subscribe("USER_REGISTERED", my_handler)
event_bus.subscribe("*", catch_all_handler)  # wildcard

# Publish
await event_bus.publish(EventMessage(
    event_type=EventType.USER_REGISTERED,
    source="login_register_engine",
    data={"user_id": "usr_123"}
))

# History
recent = event_bus.get_history("USER_REGISTERED", limit=10)
```

Features: dead letter queue, event history, subscription stats.

---

## cache.py

Two-tier caching system:

- **L1**: In-memory dict (instant, lost on restart)
- **L2**: File-based JSON in `data/cache/` (survives restart)

```python
from shared.cache import LocalCache, file_exists_locally

cache = LocalCache(namespace="my_engine", ttl=3600)
cache.set("key", {"data": "value"})
result = cache.get("key")  # L1 → L2 → None

# Check before downloading
if file_exists_locally("data/gov-data/census.json"):
    # Use local copy
else:
    # Download and cache
```

---

## nvidia_client.py

Unified NVIDIA NIM client using the OpenAI-compatible SDK.

```python
from shared.nvidia_client import nvidia_client

# Chat completion
response = await nvidia_client.chat_completion(
    messages=[{"role": "user", "content": "What is PM-KISAN?"}],
    model="meta/llama-3.1-70b-instruct"
)

# Text generation (simpler API)
text = await nvidia_client.generate_text(
    prompt="Explain PMAY in Hindi",
    system_prompt="You are a government schemes expert.",
    max_tokens=300
)

# Embeddings
vector = await nvidia_client.generate_embedding("PM-KISAN farmer scheme")
vectors = await nvidia_client.generate_embeddings_batch(["text1", "text2"])
```

---

## utils.py

### ID Generation
- `generate_id(prefix="")` → `"usr_a1b2c3d4"` or `"a1b2c3d4"`
- `generate_uuid()` → full UUID4 string

### Hashing
- `sha256_hash(data)` → hex digest
- `hash_chain(current, previous)` → chained hash for integrity

### JWT
- `create_access_token(user_id, roles)` → JWT string (30 min)
- `create_refresh_token(user_id)` → JWT string (7 days)
- `decode_token(token)` → payload dict or raises

### Indian Data
- `INDIAN_STATES` — 36 states/UTs
- `INDIAN_LANGUAGES` — 23 official languages
- `normalize_state_name(state)` → canonical name
- `format_indian_currency(amount)` → "₹1.5 Cr", "₹75 L", "₹6,000"
- `get_age_group(age)` → minor/youth/young_adult/middle_aged/senior_citizen
- `get_income_bracket(income)` → below_2.5L/2.5L-5L/5L-10L/10L-20L/above_20L

### Utilities
- `utcnow()` → current UTC datetime
- `days_until(target_date)` → days remaining
- `@timer` — decorator for execution time logging

---

## Orchestrator Context

The shared module is imported by **all 21 engines** and the **API Gateway orchestrator**. It provides the foundation for:

### Cross-Engine Communication

| Module | Orchestrator Usage |
|--------|-------------------|
| `config.py` | `ENGINE_URLS` dict — maps engine keys to `http://localhost:{port}` for all call_engine() calls |
| `models.py` | `ApiResponse` wrapper — orchestrator unwraps `data` field from engine responses |
| `event_bus.py` | Audit logging — orchestrator publishes events consumed by E3 (Raw Data Store) and E13 (Analytics) |
| `nvidia_client.py` | Used by E7 (Neural Network), E6 (Vector DB), E20 (Speech), E21 (Doc Understanding) for NIM API calls |

### Engine Port Map

| Port | Engine | Key in `ENGINE_URLS` |
|------|--------|---------------------|
| 8000 | API Gateway | `api_gateway` |
| 8001 | Login/Register | `login_register` |
| 8002 | Identity | `identity` |
| 8003 | Raw Data Store | `raw_data_store` |
| 8004 | Metadata | `metadata` |
| 8005 | Processed Metadata | `processed_metadata` |
| 8006 | Vector Database | `vector_database` |
| 8007 | Neural Network | `neural_network` |
| 8008 | Anomaly Detection | `anomaly_detection` |
| 8010 | Chunks Engine | `chunks` |
| 8011 | Policy Fetching | `policy_fetching` |
| 8012 | JSON User Info | `json_user_info` |
| 8013 | Analytics Warehouse | `analytics_warehouse` |
| 8014 | Dashboard BFF | `dashboard_bff` |
| 8015 | Eligibility Rules | `eligibility_rules` |
| 8016 | Deadline Monitoring | `deadline_monitoring` |
| 8017 | Simulation | `simulation` |
| 8018 | Gov Data Sync | `gov_data_sync` |
| 8019 | Trust Scoring | `trust_scoring` |
| 8020 | Speech Interface | `speech_interface` |
| 8021 | Doc Understanding | `doc_understanding` |

> **Note:** Port 8009 is intentionally unused.

### Configuration Override Order

1. Environment variables (highest priority)
2. `.env` file in project root
3. Default values in `Settings` class (lowest priority)

### JWT Configuration

- Algorithm: HS256 (local dev) / RS256 (production)
- Secret: loaded from `JWT_SECRET_KEY` environment variable or `.env` file
- Access token: 30-minute expiry
- Refresh token: 7-day expiry
- All engines share the same secret via `settings.JWT_SECRET_KEY`
