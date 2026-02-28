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
