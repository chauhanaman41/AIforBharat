# Engine 3 — Raw Data Store

> Append-only event store with SHA-256 hash chain integrity.

| Property | Value |
|----------|-------|
| **Port** | 8003 |
| **Folder** | `raw-data-store/` |
| **Storage** | Local filesystem (`data/raw-store/hot/YYYY/MM/DD/`) |

## Run

```bash
uvicorn raw-data-store.main:app --port 8003 --reload
```

Docs: http://localhost:8003/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/raw-data/events` | Store immutable event with hash chain |
| GET | `/raw-data/events/{event_id}` | Retrieve event by ID |
| GET | `/raw-data/events` | List recent events (filterable by type, user, date) |
| GET | `/raw-data/user/{user_id}/trail` | Full user audit trail |
| POST | `/raw-data/integrity/verify` | Verify hash chain integrity |

## Storage Architecture

```
data/raw-store/
├── hot/              # Recent events (< 30 days)
│   └── 2024/01/15/   # Date-partitioned directories
│       ├── evt_abc123.json
│       └── evt_def456.json
├── warm/             # Aged events (30-90 days)
└── cold/             # Archived events (> 90 days)
```

## Hash Chain

Every event stores `SHA-256(content + previous_hash)`. This creates an immutable, tamper-evident chain. The integrity verify endpoint validates the entire chain for a user or event type.

## Event Bus Integration

Subscribes to **all events** (`*` wildcard) — every event published anywhere in the platform is automatically stored as an immutable record.

## Request Models

- `RawEventInput` — `event_type` (str, required), `source_engine` (str, required), `user_id` (optional), `payload` (dict, default `{}`)
- `IntegrityVerifyRequest` — `event_ids` (list of str, default `[]`)

## Gateway Route

Not directly exposed via API Gateway (internal engine). Other engines write to it via event bus subscription.
