# 🏛 AIforBharat System Operating Blueprint

This document defines the end-to-end operational flow and connection map for the AIforBharat platform, aligning 21 specialized engines into a 6-layer architectural framework.

---

## 🏛 High-Level Architecture Layers

| Layer | Engines | Responsibility |
|---|---|---|
| **Layer 1: User Interaction** | `dashboard-interface`, `speech-interface-engine` | UI, Voice IVR, and User Experience |
| **Layer 2: API & Orchestration** | `api-gateway`, `login-register-engine`, `identity-engine` | Routing, Auth, JWT, and User Identity Vault |
| **Layer 3: Intelligence** | `neural-network-engine` (AI Core), `document-understanding-engine`, `json-user-info-generator`, `metadata-engine`, `trust-scoring-engine` | LLM Orchestration (NVIDIA NIM), RAG, Extraction, Normalization |
| **Layer 4: Deterministic Logic** | `eligibility-rules-engine`, `simulation-engine`, `deadline-monitoring-engine`, `anomaly-detection-engine` | Boolean Rule Evaluation, Scenarios, Date-based Alerts, Guardrails |
| **Layer 5: Data** | `policy-fetching-engine`, `government-data-sync-engine`, `raw-data-store`, `vector-database`, `processed-user-metadata-store`, `chunks-engine` | Ingestion, Semantic Chunking, Embeddings, Immutable Logs, Metadata Store |
| **Layer 6: Monitoring & Audit** | `analytics-warehouse` | Aggregated metrics, Heatmaps, Impact Modeling |

---

## 🔷 MASTER FLOWS

### 1️⃣ SYSTEM BOOTSTRAPPING FLOW (Policy Ingestion)
*Runs in background to build the system's intelligence.*

1.  **Ingestion**: `policy-fetching-engine` scrapes 100+ sources (data.gov.in, PIB, Gazette). It performs hash-based change detection.
2.  **Archival**: `raw-data-store` captures the immutable PDF/HTML snapshot with a versioned content hash.
3.  **Chunking**: `chunks-engine` breaks documents into semantic sections (512 tokens) with parent-child hierarchy.
4.  **Rule Extraction**: `document-understanding-engine` uses LLM-extraction to identify `min_age`, `income_limit`, etc., and populates the `eligibility-rules-engine` repository.
5.  **Embedding**: `chunks-engine` calls `neural-network-engine` (NV-Embed-QA via NVIDIA NIM) to generate 768-dim vectors.
6.  **Indexing**: `vector-database` stores vectors in state-partitioned collections (UP, MH, Central) with HNSW indexes.
7.  **Tagging**: `metadata-engine` adds ministry, state, and beneficiary tags to the `processed-policy-store`.

### 2️⃣ USER ONBOARDING FLOW
1.  **Registration**: `login-register-engine` handles OTP/Auth; `identity-engine` creates a tokenized identity and encrypted PII vault.
2.  **Structuring**: `metadata-engine` normalizes user inputs (Age, Income, State) into a canonical JSON schema.
3.  **Persistance**: Data is stored in the `processed-user-metadata-store`.
4.  **Precomputation**: `eligibility-rules-engine` runs a full batch check against all 1000+ schemes. Results are cached in Redis to pre-populate the `dashboard-interface`.

### 3️⃣ QUERY & RAG FLOW
1.  **Entry**: User asks a question via `speech-interface-engine` or `dashboard-interface`.
2.  **Gateway**: `api-gateway` validates JWT and routes to the `neural-network-engine` (AI Core).
3.  **Classification**: `neural-network-engine` Orchestrator (NeMo BERT) classifies intent (Informational, Eligibility, Simulation).
4.  **Retrieval**: `vector-database` performs Hybrid Search (Vector + BM25) to find the Top-K policy chunks.
5.  **Generation**: `neural-network-engine` (Llama 3.3 70B via NIM) generates a grounded answer using retrieved chunks + user metadata.
6.  **Guardrail**: `anomaly-detection-engine` verifies citations and checks for hallucination risk.
7.  **Audit**: `raw-data-store` logs the full query, context used, and response for Layer 6.

### 4️⃣ ELIGIBILITY EVALUATION FLOW
*Triggered on metadata update or user query.*

1.  **Fetch**: `metadata-engine` provides the latest normalized user profile.
2.  **Deterministic Match**: `eligibility-rules-engine` runs pure Python boolean logic (no LLM) against scheme criteria.
3.  **Explanation**: If eligible/partially-eligible, `neural-network-engine` (Llama 3.3 8B) generates a natural language explanation of the verdict.
4.  **Caching**: Results are stored in Redis for sub-100ms dashboard rendering.

### 5️⃣ SIMULATION & ALERT FLOW
1.  **Scenario**: User asks "What if my income increases to 12L?".
2.  **Cloning**: `simulation-engine` creates a temporary metadata clone with the modified values.
3.  **Re-run**: `eligibility-rules-engine` re-evaluates the entire scheme library for the "simulated" user.
4.  **Impact**: `neural-network-engine` computes the delta (Schemes lost, tax slab changes) and explains it in simple terms.
5.  **Monitoring**: `deadline-monitoring-engine` runs daily jobs to check for tax deadlines, scheme renewals, and certificate expirations, publishing events to the `dashboard-interface`.

---

## 📊 ANALYTICS & AUDIT FLOW
1.  **Aggregation**: `analytics-warehouse` (ClickHouse) ingests anonymized events from all engines via Kafka.
2.  **Impact Modeling**: `RAPIDS cuML` (XGBoost) runs on GPU to correlate scheme adoption with regional economic indicators (using local NFHS-5 and Census datasets).
3.  **Visualization**: Materialized views feed heatmaps and performance KPIs to the admin dashboard.

---

## 🔗 DEPENDENCY MAPPING

| Engine | Primary Dependencies | Output Consumer |
|---|---|---|
| `api-gateway` | `login-register-engine` (JWT) | All Backend Engines |
| `chunks-engine` | `policy-fetching-engine` | `vector-database` |
| `eligibility-rules-engine`| `metadata-engine`, `document-understanding` | `dashboard-interface` |
| `neural-network-engine` | `vector-database`, `identity-engine` | `api-gateway` (Response) |
| `simulation-engine` | `eligibility-rules-engine` | `dashboard-interface` |
| `analytics-warehouse` | `raw-data-store`, `eligibility-rules-engine` | Admin Dashboards |

---

## 🔐 TRUST & GOVERNANCE PRINCIPLES
- **Deterministic vs. Probabilistic**: Decisions (Eligibility/Tax) are ALWAYS deterministic. LLMs are EXCLUSIVELY for explanation.
- **Idempotency**: All ingestion and processing flows must be idempotent (Content hashes prevent duplicates).
- **Immutability**: `raw-data-store` uses append-only logs with SHA-256 hash chains for audit integrity.
- **Privacy**: PII is encrypted at rest (`identity-engine`) and hashed for analytics (`analytics-warehouse`).
- **NVIDIA Powered**: All Intelligence Layer operations utilize NVIDIA NIM, TensorRT-LLM, and RAPIDS for maximum throughput and accuracy.

---
*Blueprint generated for AIforBharat Workspace.*
