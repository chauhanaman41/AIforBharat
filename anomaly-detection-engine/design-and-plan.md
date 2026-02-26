# 🛡️ Anomaly Detection Engine — Design & Plan

## 1. Purpose

The Anomaly Detection Engine is the **trust and safety layer** of the AIforBharat platform. It operates on two critical fronts:

1. **AI Output Verification** — Detect hallucinations, policy mismatches, and outdated policy references in LLM outputs
2. **System Anomaly Detection** — Detect suspicious user activity, fraud patterns, and data integrity violations

This engine is **critical for government trust** — every output the platform delivers to citizens must be verifiable, accurate, and traceable.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Hallucination Detection** | Verify LLM outputs against source documents |
| **Policy Mismatch Detection** | Flag responses citing wrong or expired policies |
| **Outdated Policy Detection** | Alert when responses use superseded policy data |
| **Suspicious Activity Detection** | Flag unusual user behavior patterns |
| **Data Integrity Monitoring** | Detect tampering in Raw Data Store |
| **Model Drift Detection** | Monitor AI model performance degradation |
| **Citation Verification** | Validate every source referenced in AI outputs |
| **Fraud Pattern Detection** | Identify coordinated fake accounts or abuse |
| **Real-Time Scoring** | Score every AI response for anomaly risk |
| **Batch Audit** | Periodic comprehensive audit of all outputs |

---

## 3. Architecture

### 3.1 Two-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Anomaly Detection Engine                         │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │           Layer A: AI Output Verification                  │   │
│  │                                                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │ Hallucination│  │ Citation     │  │ Policy         │  │   │
│  │  │ Detector     │  │ Verifier     │  │ Freshness      │  │   │
│  │  │              │  │              │  │ Checker        │  │   │
│  │  │ Llama 3.1 8B │  │ Rule-based + │  │ Version DB     │  │   │
│  │  │ (2nd pass)   │  │ Vector match │  │ lookup         │  │   │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │   │
│  │                                                           │   │
│  │  ┌──────────────┐  ┌──────────────┐                      │   │
│  │  │ Consistency  │  │ Confidence   │                      │   │
│  │  │ Checker      │  │ Scorer       │                      │   │
│  │  │              │  │              │                      │   │
│  │  │ Cross-check  │  │ Aggregate    │                      │   │
│  │  │ multiple     │  │ all signals  │                      │   │
│  │  │ retrieval    │  │ into score   │                      │   │
│  │  │ results      │  │              │                      │   │
│  │  └──────────────┘  └──────────────┘                      │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │           Layer B: System Anomaly Detection                │   │
│  │                                                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │ User Behavior│  │ Data Integrity│ │ Model Drift    │  │   │
│  │  │ Anomaly      │  │ Monitor      │  │ Monitor        │  │   │
│  │  │              │  │              │  │                │  │   │
│  │  │ Autoencoder  │  │ Hash chain   │  │ Statistical    │  │   │
│  │  │ + Isolation  │  │ verification │  │ tests on       │  │   │
│  │  │ Forest       │  │              │  │ model outputs  │  │   │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │   │
│  │                                                           │   │
│  │  ┌──────────────┐  ┌──────────────┐                      │   │
│  │  │ Fraud        │  │ Rate Abuse   │                      │   │
│  │  │ Detection    │  │ Detection    │                      │   │
│  │  │              │  │              │                      │   │
│  │  │ Graph-based  │  │ Sliding      │                      │   │
│  │  │ analysis     │  │ window       │                      │   │
│  │  └──────────────┘  └──────────────┘                      │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │           Scoring & Response Layer                         │   │
│  │                                                           │   │
│  │  Input signals → Weighted aggregation → Final score       │   │
│  │  Score < 0.3: PASS (green)                                │   │
│  │  Score 0.3-0.7: REVIEW (yellow) → flag for human review   │   │
│  │  Score > 0.7: BLOCK (red) → prevent response delivery     │   │
│  └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Detection Methods

### 4.1 Hallucination Detection Pipeline

```
AI Response received
    │
    ├─► Extract claims from response (NeMo BERT NER)
    │   Example claims:
    │   - "PM-KISAN provides ₹6,000 per year"
    │   - "Applicable to landholding less than 2 hectares"
    │   - "Apply before March 31, 2026"
    │
    ├─► For each claim:
    │   │
    │   ├─► Search Vector Database for supporting evidence
    │   ├─► Compute entailment score (NLI model)
    │   ├─► Check against policy version database
    │   └─► Score: {claim, evidence_found, entailment_score, policy_current}
    │
    ├─► Second-pass LLM verification (Llama 3.1 8B)
    │   Prompt: "Given these source documents, is this response accurate?"
    │
    └─► Aggregate scores → Final hallucination risk score
```

### 4.2 User Behavior Anomaly Detection

```python
# Feature vector per user session
features = {
    "queries_per_minute": float,
    "unique_schemes_queried": int,
    "avg_query_length": float,
    "state_switching_frequency": int,   # Querying multiple states rapidly
    "simulation_count": int,
    "api_error_rate": float,
    "session_duration_minutes": float,
    "device_switch_count": int
}

# Detection models:
# 1. Isolation Forest (unsupervised, GPU-accelerated)
# 2. Autoencoder (reconstruction error threshold)
# 3. Rule-based (hard limits for known attack patterns)
```

---

## 5. Data Models

### 5.1 Anomaly Score Record

```json
{
  "anomaly_id": "uuid",
  "target_type": "ai_response",
  "target_id": "query_uuid",
  "timestamp": "2026-02-26T10:05:00Z",
  "scores": {
    "hallucination_risk": 0.15,
    "citation_validity": 0.95,
    "policy_freshness": 1.0,
    "consistency_score": 0.88,
    "overall_anomaly_score": 0.12
  },
  "verdict": "PASS",
  "details": {
    "claims_checked": 3,
    "claims_verified": 3,
    "claims_flagged": 0,
    "sources_referenced": 2,
    "sources_valid": 2
  },
  "model_version": "anomaly_v1.2",
  "processing_time_ms": 120
}
```

### 5.2 User Anomaly Alert

```json
{
  "alert_id": "uuid",
  "user_id": "uuid",
  "alert_type": "suspicious_behavior",
  "severity": "medium",
  "detected_at": "2026-02-26T10:30:00Z",
  "pattern": "rapid_state_switching",
  "evidence": {
    "states_queried": ["UP", "MH", "KA", "TN", "GJ"],
    "time_window_minutes": 2,
    "typical_rate": 1
  },
  "action_taken": "rate_limited",
  "requires_review": true
}
```

---

## 6. Context Flow

```
AI_RESPONSE_GENERATED event arrives from Event Bus
    │
    ├─► Layer A: Output Verification (real-time, < 200ms)
    │       │
    │       ├─► Extract claims from response text
    │       ├─► Verify each claim against Vector DB
    │       ├─► Check policy version currency
    │       ├─► Run NLI entailment scoring
    │       ├─► Optional: Second-pass LLM check
    │       └─► Score: hallucination_risk, citation_validity
    │
    ├─► Scoring Layer
    │       │
    │       ├─► Aggregate all Layer A signals
    │       ├─► Apply weighted scoring model
    │       ├─► Verdict: PASS / REVIEW / BLOCK
    │       └─► Publish ANOMALY_SCORED event
    │
    ├─► [If BLOCK] → Prevent response delivery, queue for human review
    ├─► [If REVIEW] → Deliver response with warning flag
    └─► [If PASS] → Deliver response with confidence score

Separately (batch / streaming):
    │
    └─► Layer B: System Anomaly Detection
            │
            ├─► Consume user activity stream
            ├─► Build feature vectors per session
            ├─► Run Isolation Forest + Autoencoder
            ├─► Apply rule-based filters
            ├─► Flag anomalous sessions
            └─► Publish ANOMALY_ALERT to Event Bus
```

---

## 7. NVIDIA Stack Alignment

| Component | NVIDIA Tool | Purpose |
|---|---|---|
| **Hallucination Detection LLM** | Llama 3.1 8B (NIM) | Second-pass verification of AI outputs |
| **NLI Model** | NeMo BERT | Natural Language Inference for claim verification |
| **Autoencoder** | NeMo Autoencoder | User behavior anomaly detection |
| **Isolation Forest** | RAPIDS cuML | GPU-accelerated unsupervised anomaly detection |
| **Feature Engineering** | RAPIDS cuDF | GPU-accelerated feature extraction from logs |
| **Model Serving** | Triton Inference Server | Serve anomaly detection models |
| **Security Analytics** | NVIDIA Morpheus | Real-time cybersecurity anomaly detection |

---

## 8. Scaling Strategy

| Scale Tier | Queries/Day | Strategy |
|---|---|---|
| **Tier 1** (MVP) | < 10K | Rule-based checks only, single GPU for LLM verification |
| **Tier 2** | 10K – 100K | Full pipeline, 2x GPU, batch auditing |
| **Tier 3** | 100K – 1M | Streaming anomaly detection, Morpheus integration |
| **Tier 4** | 1M+ | Multi-GPU cluster, edge anomaly nodes, pre-computed trust |

### Key Decisions

- **Real-time path**: Must complete in < 200ms (don't block user experience)
- **Batch path**: Comprehensive audit runs hourly/daily
- **False positive rate**: Target < 2% (too many false alarms erode trust)
- **Human review queue**: Staffed for REVIEW-verdict responses

---

## 9. API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/anomaly/verify-response` | Verify AI response (sync) |
| `POST` | `/api/v1/anomaly/score-user` | Score user session for anomalies |
| `GET` | `/api/v1/anomaly/alerts` | Get recent anomaly alerts |
| `GET` | `/api/v1/anomaly/alerts/{alert_id}` | Get specific alert details |
| `PUT` | `/api/v1/anomaly/alerts/{alert_id}/resolve` | Resolve/dismiss alert |
| `GET` | `/api/v1/anomaly/stats` | Anomaly detection statistics |
| `POST` | `/api/v1/anomaly/audit/trigger` | Trigger batch audit |

---

## 10. Dependencies

| Dependency | Direction | Purpose |
|---|---|---|
| **Neural Network Engine** | Upstream | Receives AI responses for verification |
| **Vector Database** | Upstream | Source evidence for claim verification |
| **Gov Data Sync Engine** | Upstream | Policy version currency data |
| **Trust Scoring Engine** | Downstream | Feeds anomaly scores for trust computation |
| **Raw Data Store** | Downstream | Logs all anomaly detection results |
| **Dashboard** | Downstream | Admin anomaly dashboard |
| **Event Bus** | Bidirectional | Consumes response events, publishes anomaly alerts |

---

## 11. Technology Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11 (FastAPI) |
| LLM Verification | Llama 3.1 8B (via NVIDIA NIM) |
| NLI Model | NeMo BERT (fine-tuned on policy domain) |
| Anomaly ML | RAPIDS cuML (Isolation Forest, Autoencoder) |
| Feature Store | Redis (real-time features) + PostgreSQL (historical) |
| Streaming | Apache Kafka Streams / Faust |
| Security | NVIDIA Morpheus |
| Model Serving | Triton Inference Server |
| Monitoring | Prometheus + Grafana |
| Containerization | Docker + Kubernetes |

---

## 12. Implementation Phases

| Phase | Milestone | Timeline |
|---|---|---|
| **Phase 1** | Rule-based citation checker, policy version validator | Week 1-3 |
| **Phase 2** | NLI-based claim verification pipeline | Week 4-6 |
| **Phase 3** | Second-pass LLM hallucination detection | Week 7-9 |
| **Phase 4** | User behavior anomaly detection (Isolation Forest) | Week 10-12 |
| **Phase 5** | Autoencoder for complex pattern detection | Week 13-15 |
| **Phase 6** | Morpheus integration for security analytics | Week 16-18 |
| **Phase 7** | Batch audit system, human review workflow | Week 19-20 |

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Hallucination detection rate | > 95% |
| False positive rate | < 2% |
| Verification latency (P95) | < 200ms |
| Suspicious activity detection rate | > 90% |
| Citation validity accuracy | > 98% |
| Policy freshness check accuracy | 100% |
| Batch audit coverage | 100% of responses audited within 24h |
