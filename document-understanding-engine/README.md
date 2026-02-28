# Engine 21 — Document Understanding Engine

> Parses policy documents into structured fields using hybrid rule-based + NIM LLM extraction.

| Property | Value |
|----------|-------|
| **Port** | 8021 |
| **Folder** | `document-understanding-engine/` |
| **Database Tables** | `parsed_documents` |

## Run

```bash
uvicorn document-understanding-engine.main:app --port 8021 --reload
```

Docs: http://localhost:8021/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/documents/parse` | Parse a policy document (hybrid extraction) |
| POST | `/documents/parse/batch` | Batch parse multiple documents |
| GET | `/documents/parsed/{parsed_id}` | Get parsed document by ID |
| GET | `/documents/by-policy/{policy_id}` | Get all parsed docs for a policy |

## Extraction Pipeline

### Step 1: Rule-Based Extraction

Keyword matching against the document text:

| Field | Keywords Scanned |
|-------|-----------------|
| `eligibility_criteria` | "eligible", "eligibility", "criteria", "qualification" |
| `benefits` | "benefit", "entitlement", "assistance", "subsidy" |
| `required_documents` | "documents required", "proof", "certificate" |
| `deadlines` | "deadline", "last date", "due date", "apply before" |
| `amounts` | Regex for ₹, Rs., Rupees patterns |
| `age_limits` | Age range patterns (e.g., "18-65 years") |
| `income_limits` | Income threshold patterns |
| `categories` | SC, ST, OBC, EWS, BPL, APL mentions |

### Step 2: NIM LLM Extraction

Sends the full document text to Llama 3.1 70B with a structured extraction prompt. Asks for JSON output with scheme_name, eligibility, benefits, amounts, deadlines, documents_needed, categories.

### Step 3: Hybrid Merge

- NIM results take priority for each field
- Rule-based results fill gaps where NIM didn't extract
- Both sources recorded in output

## Request Models

- `ParseDocumentRequest` — `policy_id`, `content` (full text), `title`, `source`
- `BatchParseRequest` — `documents` (list of ParseDocumentRequest)

## Events Published

- `DOCUMENT_PROCESSED` — on successful parse

## Pipeline Role

```
Engine 11 (fetch) → Engine 21 (parse) → Engine 10 (chunk) → Engine 6 (embed)
```

## Gateway Route

`/api/v1/documents/*` → proxied from API Gateway (JWT auth required)

## Orchestrator Integration

This engine participates in the following composite flows orchestrated by the API Gateway:

| Flow | Route | Role | Step |
|------|-------|------|------|
| **Policy Ingestion** | `POST /api/v1/ingest-policy` | Parse raw policy text into structured fields | Step 2 of 7 |

### Flow Detail: Policy Ingestion

```
E11 (Fetch) → E21 (Parse) → E10 (Chunk) → E7 (Embed) → E6 (Vector Upsert)
  → E4 (Tag Metadata) → E3+E13 (Audit)
```

E21 receives the raw fetched text from E11 and extracts structured fields using a 3-step hybrid pipeline (rule-based → NIM LLM → merged). Failure is **non-critical** — the pipeline continues with raw text for chunking.

### 3-Step Extraction Pipeline

1. **Rule-Based Extraction:** Keyword matching for eligibility criteria, benefits, documents required, deadlines, monetary amounts, categories
2. **NIM LLM Extraction:** Llama 3.1 70B structured prompt → JSON output with scheme_name, ministry, eligibility, benefits, etc.
3. **Hybrid Merge:** NIM results take priority, rule-based fills gaps where NIM missed

## Inter-Engine Dependencies

| Direction | Engine | Purpose |
|-----------|--------|--------|
| **Called by** | API Gateway (Orchestrator) | `/documents/parse` during policy ingestion |
| **Called by** | API Gateway (Proxy) | All `/documents/*` routes for direct access |
| **Fed by** | Policy Fetching (E11) | Raw document text |
| **Feeds** | Chunks Engine (E10) | Parsed/cleaned text for chunking |
| **Feeds** | Metadata Engine (E4) | Structured fields (ministry, scheme_type) |
| **Depends on** | NVIDIA NIM API | LLM-based structured extraction |
| **Publishes to** | Event Bus → E3, E13 | `DOCUMENT_PARSED` |

## Shared Module Dependencies

- `shared/config.py` — `settings` (NIM model ID, port)
- `shared/database.py` — `Base`, `AsyncSessionLocal`, `init_db()`
- `shared/models.py` — `ApiResponse`, `HealthResponse`, `EventMessage`, `EventType`
- `shared/event_bus.py` — `event_bus`
- `shared/nvidia_client.py` — `nvidia_client` (LLM extraction)
- `shared/utils.py` — `generate_id()`
- `shared/cache.py` — `LocalCache`
