# AI-Assistant Features Implementation Plan (AIforBharat)

This document outlines the implementation plan for the requested AI-assistant features, mapping them to the 21 specialized engines of the AIforBharat ecosystem and defining the storage and connection strategy.

---

## 🏛️ 1. Civic Information & Public Service Assistants

### 1. Government Scheme Navigator
*   **Engine Connection**:
    *   `E15 (Eligibility Rules)`: Performs deterministic matching of user metadata against scheme criteria.
    *   `E11 (Policy Fetching)`: Retrieves the latest scheme documents.
    *   `E7 (Neural Network)`: Generates natural language explanations of benefits and guidance.
    *   `E20 (Speech Interface)`: Provides voice-first interaction for low-literacy users.
*   **Data Flow**: User Profile (`E5`) → Eligibility Match (`E15`) → Context Retrieval (`E6`) → LLM Explanation (`E7`) → Voice Output (`E20`).
*   **Storage**: Results cached in `user_eligibility_cache` table in `aiforbharat.db`.

### 2. Public Grievance & Complaint Assistant
*   **Engine Connection**:
    *   `E20 (Speech Interface)`: Captures voice complaints.
    *   `E7 (Neural Network)`: Extracts structured data (category, location, issue) from voice.
    *   `E16 (Deadline Monitoring)`: Tracks complaint resolution timelines and triggers escalation.
*   **Data Flow**: Audio Input (`E20`) → Entity Extraction (`E7`) → Log Entry (`E3`) → Alert Setup (`E16`).
*   **Storage**: Structured complaints in a new `grievances` table; raw audio in `data/audio/`.

### 3. Document & Form Filling Assistant
*   **Engine Connection**:
    *   `E21 (Document Understanding)`: Parses document scans and identifies fields.
    *   `E12 (JSON User Info)`: Supplies verified user data for auto-filling.
    *   `E7 (Neural Network)`: Explains document clauses in simple language.
*   **Data Flow**: Document Image/Text (`E21`) ←→ User Metadata (`E5`) → LLM Explanation (`E7`).
*   **Storage**: Parsed results in `parsed_documents`.

---

## 🎓 2. Education & Skill Development Assistants

### 4. Local Language Learning Assistant
*   **Engine Connection**:
    *   `E7 (Neural Network)`: Acts as a multilingual tutor (Llama 3.3 via NIM).
    *   `E20 (Speech Interface)`: Handles pronunciation checks and voice tutoring.
*   **Data Flow**: Speech Input (`E20`) → Translation/Correction (`E7`) → Voice Feedback (`E20`).
*   **Storage**: `learning_progress` tracked in `user_metadata`.

### 5. Career & Job Matching Assistant
*   **Engine Connection**:
    *   `E6 (Vector Database)`: Semantically matches user skills to job descriptions.
    *   `E7 (Neural Network)`: Generates resumes and provides interview practice.
*   **Data Flow**: User Skills (`E5`) → Semantic Search (`E6`) → Job Listings (`E18`) → LLM Resume Gen (`E7`).
*   **Storage**: `job_matches` in SQLite.

### 6. Farmer Support Assistant
*   **Engine Connection**:
    *   `E18 (Gov Data Sync)`: Fetches weather, market prices, and subsidy data.
    *   `E7 (Neural Network)`: Processes image uploads for pest diagnosis (Multimodal NIM).
*   **Data Flow**: Geo-location/Image → Data Retrieval (`E18`) → Expert Advice (`E7`).
*   **Storage**: Localized agriculture datasets in `gov_data_records`.

---

## 🏥 3. Health & Social Welfare Assistants

### 7. Primary Health Information Assistant
*   **Engine Connection**:
    *   `E18 (Gov Data Sync)`: Locates nearby hospitals and vaccination centers (NFHS-5 data).
    *   `E7 (Neural Network)`: Provides non-diagnostic symptom guidance.
    *   `E16 (Deadline Monitoring)`: Manages vaccination and maternal health reminders.
*   **Data Flow**: Symptom/Location → Resource Discovery (`E18`) → Alert Scheduling (`E16`).
*   **Storage**: `hospital_directory` and `user_health_alerts` in SQLite.

### 8. Senior Citizen Support Assistant
*   **Engine Connection**:
    *   `E15 (Eligibility Rules)`: Checks for pension and social security eligibility.
    *   `E16 (Deadline Monitoring)`: Sends medication and renewal reminders.
    *   `E20 (Speech Interface)`: Primary voice-only interface mode.
*   **Storage**: `medication_reminders` table.

---

## 💰 4. Financial Inclusion Assistants

### 9. Microfinance & Benefits Advisor
*   **Engine Connection**:
    *   `E17 (Simulation Engine)`: Calculates EMI scenarios and "what-if" loan impacts.
    *   `E19 (Trust Scoring)`: Assesses user financial readiness/trust for benefit programs.
*   **Data Flow**: Financial Inputs → Simulation (`E17`) → Trust Assessment (`E19`) → Guidance (`E7`).
*   **Storage**: `simulation_records` and `trust_scores`.

### 10. Market Access Assistant (Artisans/Small Business)
*   **Engine Connection**:
    *   `E7 (Neural Network)`: Translates product descriptions and suggests competitive pricing.
    *   `E13 (Analytics Warehouse)`: Analyzes regional demand trends.
*   **Data Flow**: Product Data → Translation/Pricing (`E7`) ← Trend Analysis (`E13`).

---

## 🗣️ 5. Accessibility-Focused Assistants

### 11. Voice-First Multilingual Assistant
*   **Engine Connection**:
    *   `E20 (Speech Interface)`: Supports 13+ regional languages.
    *   `E7 (Neural Network)`: Real-time translation and low-literacy content simplification.
*   **Storage**: `voice_sessions` history.

### 12. Assistive AI for People with Disabilities
*   **Engine Connection**:
    *   `E7 (Neural Network)`: Visual scene description and sign language tutor logic.
    *   `E20 (Speech Interface)`: Enhanced TTS for screen reading.

---

## 🌆 6. Community & Public System Intelligence

### 13. Local Resource Discovery Assistant
*   **Engine Connection**:
    *   `E18 (Gov Data Sync)`: Central repository for local amenities (Ration shops, Schools, NGOs).
    *   `E6 (Vector Database)`: Handles "near me" semantic queries.
*   **Data Flow**: Location Query → Vector Search (`E6`) → Resource Retrieval (`E18`).

### 14. Community Insights Dashboard
*   **Engine Connection**:
    *   `E13 (Analytics Warehouse)`: Aggregates anonymized events from all engines.
    *   `E14 (Dashboard Interface)`: Visualizes heatmaps and issue trends.
*   **Data Flow**: Engine Events (`*`) → Aggregation (`E13`) → Materialized Views → Dashboard UI.
*   **Storage**: `analytics_events` and `metric_snapshots` (ClickHouse or SQLite).

---

## 🚀 Connection & Storage Summary

| Component | Strategy |
| :--- | :--- |
| **Orchestration** | Chained via **API Gateway (Orchestrator)** using composite routes (e.g., `/api/v1/onboard`, `/api/v1/query`). |
| **Database** | Primary structured data in `data/aiforbharat.db` (SQLite/SQLAlchemy). |
| **Vectors** | Embeddings and semantic chunks in `vector-database` (`E6`). |
| **Audit/Logs** | Immutable logs in `raw-data-store` (`E3`) with hash chains for integrity. |
| **LLM Gateway** | All AI operations routed through `neural-network-engine` (`E7`) using **NVIDIA NIM** for performance. |
| **Multilingual** | Coordinated between `speech-interface-engine` (`E20`) and `E7` translation modules. |

---

## 🛑 7. Architectural Rectifications & Suggestions

Based on the strict **local-first** and **zero-cloud** constraints of the AIforBharat platform, the following necessary rectifications and suggestions must be applied to the plan:

### 1. Database Strictness (Analytics Warehouse)
*   **Rectification (Section 6 - Dashboard/Analytics):** The plan mentions `ClickHouse or SQLite` for analytics events. You must **remove ClickHouse**. The platform strictly mandates using `SQLite` via `aiosqlite` (WAL mode) for all databases, including engine `E13`. Any complex analytics queries should rely on pre-computed local views or Python-based aggregation to avoid external DBMS dependencies.

### 2. Trust Scoring Limits (Microfinance - E19)
*   **Rectification:** Since the use of DigiLocker and external banking APIs is strictly blocked or stubbed, `E19 (Trust Scoring)` cannot do real external background checks. It must calculate the score (0-100) purely based on internal platform signals: metadata consistency (`E5`), absence of anomalies (`E8`), and immutable hash-chain event history (`E3`).

### 3. Event-Driven Decoupling
*   **Suggestion:** Several flows (e.g., Public Grievance `E20` → `E7` → `E16`) should NOT use synchronous HTTP calls. The architecture relies on an in-memory pub/sub Event Bus (`shared/event_bus.py`). For instance, after `E7` extracts grievance details, it should publish a `GRIEVANCE_REGISTERED` event. `E16` (Deadline Monitoring) and `E3` (Raw Data Store) will independently subscribe to this event.

### 4. Multimodal Limits (Farmer Support - E7)
*   **Suggestion:** For image uploads (pest diagnosis), ensure `shared/nvidia_client.py` supports base64 encoding for multimodal NIMs (like LLaVA). Furthermore, uploaded images must be saved strictly to the local filesystem (e.g., `data/uploads/`) and adhere to the Right-to-Erasure (DPDP Compliance) by allowing cryptographic deletion or automatic purging post-session. External systems like AWS S3 are strictly forbidden.

### 5. API Gateway Strict Routing
*   **Suggestion:** The UI should never directly speak to `E7`, `E20`, or `E15`. All new assistant functions must expose their endpoints exclusively through the **API Gateway (E9)** on port `8000`, which will enforce JWT Auth and Rate Limiting before proxying to the respective orchestrating engines.
