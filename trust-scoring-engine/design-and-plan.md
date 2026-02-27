# Trust Scoring Engine — Design & Plan

## 1. Purpose

The Trust Scoring Engine provides a **confidence score, source trace, and data freshness timestamp** for every output the AIforBharat platform produces. Every scheme recommendation, eligibility verdict, simulation result, and AI-generated text is annotated with a trust signal that tells the citizen and the system: "How confident are we in this information, where did it come from, and when was it last verified?"

This engine is the **epistemic layer** — it transforms raw outputs into trustworthy, auditable information by quantifying uncertainty and providing provenance.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Confidence Scoring** | Assign Low / Medium / High confidence to every output with numerical score (0.0–1.0) |
| **Source Tracing** | Attach provenance chain: which engines, data sources, and models contributed |
| **Data Freshness Tracking** | Timestamp when each piece of source data was last verified/updated |
| **Multi-Dimensional Trust** | Separate scores for: data quality, model confidence, source authority, temporal freshness |
| **Trust Aggregation** | Combine sub-scores into composite trust indicator for user-facing displays |
| **Decay Modeling** | Trust scores decay over time as data ages (configurable decay curves) |
| **Source Authority Ranking** | Rank sources by reliability (gazette > portal > news > social media) |
| **Trust Alerts** | Flag outputs where trust falls below configurable thresholds |
| **Explainable Trust** | Generate human-readable explanation of why trust is high/low |
| **Trust Analytics** | Platform-wide trust distribution metrics for monitoring |

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Trust Scoring Engine                        │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                Trust Computation Core                      │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │ │
│  │  │ Data       │  │ Model      │  │ Source           │    │ │
│  │  │ Quality    │  │ Confidence │  │ Authority        │    │ │
│  │  │ Scorer     │  │ Scorer     │  │ Scorer           │    │ │
│  │  │            │  │            │  │                  │    │ │
│  │  │ Complete-  │  │ LLM logit  │  │ gazette: 1.0     │    │ │
│  │  │ ness,      │  │ probabil-  │  │ portal: 0.8      │    │ │
│  │  │ recency,   │  │ ities,     │  │ news: 0.5        │    │ │
│  │  │ consistency│  │ anomaly    │  │ user: 0.3        │    │ │
│  │  │            │  │ check      │  │                  │    │ │
│  │  └────────────┘  └────────────┘  └──────────────────┘    │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐                           │ │
│  │  │ Temporal   │  │ Composite  │                           │ │
│  │  │ Freshness  │  │ Aggregator │                           │ │
│  │  │ Scorer     │  │            │                           │ │
│  │  │            │  │ Weighted   │                           │ │
│  │  │ Decay over │  │ combination│                           │ │
│  │  │ time       │  │ → final    │                           │ │
│  │  └────────────┘  └────────────┘                           │ │
│  └──────────────────────────┬───────────────────────────────┘ │
│                             │                                  │
│  ┌──────────────────────────▼───────────────────────────────┐ │
│  │                Trust Classification (NeMo)                 │ │
│  │                                                            │ │
│  │  NeMo Classification Head: score → Low / Medium / High    │ │
│  │                                                            │ │
│  │  Low:    0.0 – 0.4  → "Verify independently"             │ │
│  │  Medium: 0.4 – 0.7  → "Generally reliable, check dates"  │ │
│  │  High:   0.7 – 1.0  → "Verified from official sources"   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                Provenance Tracker                          │ │
│  │                                                            │ │
│  │  Source chain: User Input → Metadata Engine → Eligibility │ │
│  │  Rules Engine → Neural Network → Dashboard                │ │
│  │                                                            │ │
│  │  Each hop annotated with: engine_id, version, timestamp   │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Data Models

### 4.1 Trust Score Object

```json
{
  "trust_id": "trust_uuid_v4",
  "target_type": "eligibility_result",
  "target_id": "eval_uuid_v4",
  "user_id": "usr_123",
  "computed_at": "2025-01-15T10:30:00Z",
  
  "composite_score": 0.87,
  "classification": "high",
  
  "dimensions": {
    "data_quality": {
      "score": 0.92,
      "factors": {
        "profile_completeness": 0.85,
        "data_consistency": 0.98,
        "no_conflicting_sources": true
      }
    },
    "model_confidence": {
      "score": 0.88,
      "factors": {
        "rule_match_certainty": 1.0,
        "llm_explanation_confidence": 0.76,
        "anomaly_check_passed": true
      }
    },
    "source_authority": {
      "score": 0.90,
      "factors": {
        "primary_source": "gazette_notification",
        "source_tier": 1,
        "verified_by_human": false
      }
    },
    "temporal_freshness": {
      "score": 0.78,
      "factors": {
        "data_age_hours": 48,
        "last_source_sync": "2025-01-13T12:00:00Z",
        "decay_applied": true,
        "decay_curve": "linear"
      }
    }
  },
  
  "provenance": {
    "chain": [
      {
        "engine": "identity_engine",
        "version": "1.2.0",
        "data_timestamp": "2025-01-10T08:00:00Z",
        "contribution": "identity verification"
      },
      {
        "engine": "metadata_engine",
        "version": "1.1.0",
        "data_timestamp": "2025-01-14T10:00:00Z",
        "contribution": "demographics, income data"
      },
      {
        "engine": "eligibility_rules_engine",
        "version": "1.3.0",
        "data_timestamp": "2025-01-15T10:30:00Z",
        "contribution": "eligibility evaluation (rule v3)"
      }
    ],
    "source_documents": [
      {
        "type": "gazette",
        "reference": "GOI/2024/EO/456",
        "date": "2024-12-01",
        "authority_score": 1.0
      }
    ]
  },
  
  "explanation": {
    "text": "High confidence: This eligibility result is based on your verified Aadhaar identity, recent income data (48 hours old), and rules sourced from an official gazette notification. The eligibility determination is 100% rule-based (no AI uncertainty).",
    "language": "en"
  },
  
  "alerts": []
}
```

### 4.2 Trust Score with Alerts (Low Confidence Example)

```json
{
  "composite_score": 0.35,
  "classification": "low",
  
  "alerts": [
    {
      "type": "stale_data",
      "severity": "warning",
      "message": "Income data is 90 days old — consider updating your profile",
      "field": "economic.annual_income",
      "last_updated": "2024-10-15T00:00:00Z"
    },
    {
      "type": "unverified_source",
      "severity": "caution",
      "message": "Scheme information sourced from news report, not official gazette",
      "source": "news_article",
      "authority_score": 0.4
    }
  ]
}
```

### 4.3 Source Authority Configuration

```python
SOURCE_AUTHORITY_TIERS = {
    # Tier 1: Official government publications (score: 0.9-1.0)
    "gazette_notification": 1.0,
    "government_portal": 0.95,
    "official_circular": 0.93,
    "budget_document": 0.98,
    "legislative_act": 1.0,
    
    # Tier 2: Semi-official sources (score: 0.6-0.8)
    "government_press_release": 0.80,
    "department_website": 0.75,
    "pib_release": 0.78,
    "data_gov_in_api": 0.85,
    
    # Tier 3: Secondary sources (score: 0.3-0.5)
    "news_report": 0.50,
    "expert_analysis": 0.45,
    "ngo_publication": 0.40,
    
    # Tier 4: Unverified (score: 0.1-0.2)
    "social_media": 0.15,
    "user_report": 0.20,
    "unattributed": 0.10
}
```

### 4.4 Trust Score Table (PostgreSQL)

```sql
CREATE TABLE trust_scores (
    trust_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_type       VARCHAR(32) NOT NULL,  -- eligibility, recommendation, simulation, ai_response
    target_id         UUID NOT NULL,
    user_id           UUID NOT NULL,
    
    composite_score   REAL NOT NULL CHECK (composite_score BETWEEN 0 AND 1),
    classification    VARCHAR(10) NOT NULL,  -- low, medium, high
    
    data_quality_score    REAL NOT NULL,
    model_confidence_score REAL NOT NULL,
    source_authority_score REAL NOT NULL,
    temporal_freshness_score REAL NOT NULL,
    
    provenance        JSONB NOT NULL,
    alerts            JSONB DEFAULT '[]',
    
    computed_at       TIMESTAMPTZ DEFAULT NOW(),
    expires_at        TIMESTAMPTZ  -- When trust score should be recomputed
) PARTITION BY RANGE (computed_at);

CREATE INDEX idx_trust_target ON trust_scores (target_type, target_id);
CREATE INDEX idx_trust_user ON trust_scores (user_id, computed_at DESC);
CREATE INDEX idx_trust_low ON trust_scores (classification) WHERE classification = 'low';
```

### 4.5 Temporal Decay Model

```python
import math
from datetime import datetime, timedelta

def compute_freshness_score(
    data_timestamp: datetime,
    current_time: datetime,
    decay_curve: str = "exponential",
    half_life_hours: float = 168  # 7 days
) -> float:
    """Compute temporal freshness score with configurable decay."""
    
    age_hours = (current_time - data_timestamp).total_seconds() / 3600
    
    if age_hours <= 0:
        return 1.0
    
    if decay_curve == "linear":
        max_age_hours = half_life_hours * 2
        return max(0.0, 1.0 - (age_hours / max_age_hours))
    
    elif decay_curve == "exponential":
        # Half-life decay: score halves every `half_life_hours`
        return math.pow(0.5, age_hours / half_life_hours)
    
    elif decay_curve == "step":
        # Step function: full score within threshold, penalty outside
        if age_hours <= half_life_hours:
            return 1.0
        elif age_hours <= half_life_hours * 2:
            return 0.5
        else:
            return 0.2
    
    return 0.5  # fallback


def aggregate_trust_score(
    data_quality: float,
    model_confidence: float,
    source_authority: float,
    temporal_freshness: float,
    weights: dict = None
) -> float:
    """Weighted aggregation of trust dimensions."""
    
    w = weights or {
        "data_quality": 0.25,
        "model_confidence": 0.25,
        "source_authority": 0.30,
        "temporal_freshness": 0.20
    }
    
    composite = (
        data_quality * w["data_quality"] +
        model_confidence * w["model_confidence"] +
        source_authority * w["source_authority"] +
        temporal_freshness * w["temporal_freshness"]
    )
    
    return round(min(1.0, max(0.0, composite)), 3)
```

---

## 5. Context Flow

```
Every Engine Output
  │
  │  Attach metadata: engine_id, version, timestamp, source_refs
  │
  ▼
┌────────────────────────────────────────────┐
│          Trust Scoring Pipeline             │
│                                            │
│  Step 1: Extract Provenance               │
│    - Which engines contributed?            │
│    - What source documents?               │
│    - When was data last verified?          │
│                                            │
│  Step 2: Score Dimensions                 │
│    ┌─────────────┐ ┌─────────────────┐    │
│    │ Data Quality │ │ Model Confidence│    │
│    │             │ │                 │    │
│    │ Completeness│ │ Rule certainty  │    │
│    │ Consistency │ │ LLM logit prob  │    │
│    │ Validation  │ │ Anomaly passed  │    │
│    └─────────────┘ └─────────────────┘    │
│    ┌─────────────┐ ┌─────────────────┐    │
│    │ Source Auth  │ │ Freshness       │    │
│    │             │ │                 │    │
│    │ Tier lookup │ │ Age decay       │    │
│    │ Gazette=1.0 │ │ Exponential     │    │
│    │ News=0.5    │ │ Half-life: 7d   │    │
│    └─────────────┘ └─────────────────┘    │
│                                            │
│  Step 3: Aggregate                        │
│    Weighted sum → composite (0.0–1.0)     │
│                                            │
│  Step 4: Classify (NeMo)                  │
│    Low / Medium / High                     │
│                                            │
│  Step 5: Generate Alerts                  │
│    If any dimension < threshold → alert    │
│                                            │
│  Step 6: Explain                          │
│    Human-readable trust explanation        │
└──────────────────┬─────────────────────────┘
                   │
      ┌────────────┼────────────┐
      ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Target   │ │ Cache    │ │ Event    │
│ Response │ │ (Redis)  │ │ Bus      │
│ (inline) │ │ TTL: 1h  │ │          │
│          │ │          │ │ trust.   │
│ Attached │ │          │ │ score.   │
│ to every │ │          │ │ updated  │
│ API resp │ │          │ │          │
└──────────┘ └──────────┘ └──────────┘
```

---

## 6. Event Bus Integration

### Consumed Events

| Event | Source | Action |
|---|---|---|
| `eligibility.computed` | Eligibility Rules Engine | Score eligibility result trust |
| `ai.response.generated` | Neural Network Engine | Score AI output trust |
| `simulation.result.ready` | Simulation Engine | Score simulation result trust |
| `policy.amended` | Government Data Sync Engine | Recompute trust for affected outputs |
| `anomaly.detected` | Anomaly Detection Engine | Lower trust scores for flagged outputs |
| `profile.assembled` | JSON User Info Generator | Compute overall profile trust |

### Published Events

| Event | Payload | Consumers |
|---|---|---|
| `trust.score.updated` | `{ target_type, target_id, composite_score, classification }` | JSON User Info Generator, Dashboard |
| `trust.alert.raised` | `{ target_id, alert_type, severity, message }` | Dashboard, Anomaly Detection |
| `trust.low_confidence` | `{ user_id, target_type, score, reason }` | Neural Network (trigger re-evaluation) |

---

## 7. NVIDIA Stack Alignment

| NVIDIA Tool | Component | Usage |
|---|---|---|
| **NeMo Classification Head** | Trust Classifier | Classify composite score → Low/Medium/High labels |
| **NeMo BERT** | Explanation Quality | Assess LLM-generated explanation quality as model confidence input |
| **NIM** | Trust Explanation | Llama 3.1 8B generates human-readable trust explanations |
| **Triton** | Model Serving | Serve classification head and quality assessment models |

### NeMo Trust Classification

```python
class TrustClassifier:
    """NeMo-based trust classification head."""
    
    def __init__(self):
        self.model = load_nemo_classifier("trust-classification-head")
    
    async def classify(self, composite_score: float, dimensions: dict) -> dict:
        """Classify trust level using NeMo classification model."""
        
        # Feature vector for classification
        features = {
            "composite_score": composite_score,
            "data_quality": dimensions["data_quality"]["score"],
            "model_confidence": dimensions["model_confidence"]["score"],
            "source_authority": dimensions["source_authority"]["score"],
            "temporal_freshness": dimensions["temporal_freshness"]["score"],
            "alert_count": len(dimensions.get("alerts", [])),
            "source_tier": dimensions["source_authority"]["factors"].get("source_tier", 3)
        }
        
        result = await self.model.predict(features)
        
        return {
            "classification": result.label,  # "low", "medium", "high"
            "confidence": result.score,
            "threshold_used": {
                "low_upper": 0.4,
                "medium_upper": 0.7,
                "high_upper": 1.0
            }
        }
```

---

## 8. Scaling Strategy

| Tier | Users | Strategy |
|---|---|---|
| **MVP** | < 10K | Inline computation (synchronous with each API response), Redis cache |
| **Growth** | 10K–500K | Async trust scoring via Kafka, batch recomputation on source updates |
| **Scale** | 500K–5M | Pre-computed trust scores for common paths, background decay updates |
| **Massive** | 5M–50M+ | Materialized trust views, regional trust scoring workers, real-time streaming decay |

---

## 9. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/trust/{target_type}/{target_id}` | Get trust score for specific output |
| `GET` | `/api/v1/trust/user/{user_id}/summary` | User's overall trust profile |
| `GET` | `/api/v1/trust/user/{user_id}/alerts` | Active trust alerts for user |
| `POST` | `/api/v1/trust/compute` | Compute trust score on-demand |
| `GET` | `/api/v1/trust/sources` | Source authority registry |
| `GET` | `/api/v1/trust/analytics/distribution` | Platform-wide trust distribution |
| `GET` | `/api/v1/trust/analytics/trends` | Trust score trends over time |

---

## 10. Dependencies

### Upstream (All engines provide metadata)

| Engine | Data Provided |
|---|---|
| All Engines | engine_id, version, timestamp, source references |
| Anomaly Detection Engine | Anomaly flags, hallucination checks |
| Government Data Sync Engine | Source authority classifications, data freshness |
| Identity Engine | Identity verification confidence |
| Policy Fetching Engine | Source URLs, crawl timestamps |

### Downstream

| Engine | Data Consumed |
|---|---|
| JSON User Info Generator | Trust section in assembled profile |
| Dashboard Interface | Confidence indicators, freshness badges |
| Neural Network Engine | Trust-weighted context for reasoning |
| Anomaly Detection Engine | Low-trust alerts as anomaly signals |
| Analytics Warehouse | Platform-wide trust metrics |

---

## 11. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| Cache | Redis 7.x (trust score cache, TTL: 1 hour) |
| Database | PostgreSQL 16 (trust score history) |
| Classification | NVIDIA NeMo (classification head) |
| Explanation | NVIDIA NIM (Llama 3.1 8B) |
| Decay Model | Custom Python (exponential/linear/step) |
| Event Bus | Apache Kafka |
| Monitoring | Prometheus + Grafana |

---

## 12. Implementation Phases

### Phase 1 — Foundation (Weeks 1-2)
- Define trust score schema and 4-dimension model
- Implement source authority tier registry
- Build temporal freshness decay model (exponential)
- Inline trust scoring for eligibility results

### Phase 2 — Classification & Provenance (Weeks 3-4)
- NeMo classification head (Low/Medium/High)
- Provenance chain tracking across engines
- Trust alerts for stale data and unverified sources
- Redis caching of computed trust scores

### Phase 3 — Explanation & Analytics (Weeks 5-6)
- NIM-powered trust explanation generation
- Platform-wide trust distribution dashboard
- Trust trend analytics (Grafana)
- Background decay recomputation

### Phase 4 — Scale (Weeks 7-8)
- Async trust scoring via Kafka
- Batch recomputation on source updates
- Pre-computed trust scores for common output types
- Trust-weighted context for Neural Network Engine

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Trust score computation latency | < 50ms (inline) |
| Trust classification accuracy | > 95% (vs human judgment) |
| Source authority coverage | 100% of tracked sources |
| Temporal decay accuracy | < 5% deviation from expected curves |
| Trust alert precision | > 90% (alerts are actionable) |
| User trust in platform (survey) | > 4.0/5.0 |
| Low-confidence output catch rate | > 95% |
| Provenance chain completeness | 100% of outputs traced |
| Trust score cache hit ratio | > 70% |
| Platform average trust score | > 0.7 (high confidence) |

---

## 14. Security Hardening

### 14.1 Rate Limiting

<!-- SECURITY: Trust scoring is called inline on every AI response.
     External query endpoints need rate limits; internal endpoints need throughput caps.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  # SECURITY: Trust score query — user-facing
  "/api/v1/trust/score/{response_id}":
    per_user:
      requests_per_minute: 30
      burst: 10
    per_ip:
      requests_per_minute: 20

  # SECURITY: Source authority lookup
  "/api/v1/trust/sources":
    per_user:
      requests_per_minute: 20
      burst: 5

  # SECURITY: Trust score override — admin only, high sensitivity
  "/api/v1/trust/override":
    per_user:
      requests_per_minute: 5
      burst: 1
    require_role: admin
    require_mfa: true

  # SECURITY: Provenance chain retrieval
  "/api/v1/trust/provenance/{response_id}":
    per_user:
      requests_per_minute: 15

  # SECURITY: Internal inline scoring (called by Neural Network Engine)
  internal_endpoints:
    "/internal/trust/compute":
      per_service:
        requests_per_second: 200
      allowed_callers: ["neural-network-engine", "anomaly-detection-engine"]

  rate_limit_response:
    status: 429
    body:
      error: "rate_limit_exceeded"
      message: "Trust scoring rate limit reached."
```

### 14.2 Input Validation & Sanitization

<!-- SECURITY: Trust scoring inputs include AI-generated text and source references.
     Validation prevents score manipulation and provenance poisoning.
     OWASP Reference: API3:2023, API8:2023 -->

```python
# SECURITY: Trust score computation request schema
TRUST_SCORE_REQUEST_SCHEMA = {
    "type": "object",
    "required": ["response_id", "response_text", "sources"],
    "additionalProperties": False,
    "properties": {
        "response_id": {
            "type": "string",
            "pattern": "^resp_[a-zA-Z0-9]{12,32}$"
        },
        "response_text": {
            "type": "string",
            "minLength": 1,
            "maxLength": 10000
        },
        "sources": {
            "type": "array",
            "maxItems": 20,
            "items": {
                "type": "object",
                "required": ["source_id", "authority_level"],
                "additionalProperties": False,
                "properties": {
                    "source_id": {"type": "string", "pattern": "^src_[a-zA-Z0-9]+$"},
                    "authority_level": {"type": "string", "enum": ["gazette", "act", "notification", "guideline", "faq", "news", "community"]},
                    "publication_date": {"type": "string", "format": "date"},
                    "url": {"type": "string", "format": "uri", "maxLength": 500}
                }
            }
        },
        "query_context": {
            "type": "string",
            "maxLength": 2000
        }
    }
}

# SECURITY: Trust score override schema — admin only
TRUST_OVERRIDE_SCHEMA = {
    "type": "object",
    "required": ["response_id", "override_score", "reason"],
    "additionalProperties": False,
    "properties": {
        "response_id": {"type": "string", "pattern": "^resp_[a-zA-Z0-9]{12,32}$"},
        "override_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reason": {"type": "string", "minLength": 10, "maxLength": 500}
    }
}
```

### 14.3 Secure API Key & Secret Management

```yaml
secrets_management:
  environment_variables:
    - DB_PASSWORD               # PostgreSQL (trust scores, provenance)
    - REDIS_PASSWORD            # Trust score cache
    - KAFKA_SASL_PASSWORD       # Event bus auth
    - NIM_API_KEY               # NLI model for claim verification
    - MILVUS_API_KEY            # Vector DB for source matching

  rotation_policy:
    db_credentials: 90_days
    nim_api_key: 180_days
    service_tokens: 90_days

  # SECURITY: Trust score manipulation is a critical threat
  integrity_controls:
    scores_are_append_only: true    # Cannot delete/update historical scores
    override_requires_audit_trail: true
    provenance_chains_immutable: true
```

### 14.4 OWASP Compliance

| OWASP Risk | Mitigation |
|---|---|
| **API1: BOLA** | Trust scores scoped to user's own responses; admin for cross-user access |
| **API2: Broken Auth** | JWT validation; override endpoint requires admin + MFA |
| **API3: Broken Property Auth** | Strict schemas; authority_level enum prevents score inflation |
| **API4: Resource Consumption** | Inline scoring capped per service; user queries rate-limited |
| **API5: Broken Function Auth** | Override restricted to admin; auditor role is read-only |
| **API6: Sensitive Flows** | Score overrides logged immutably; require reason field |
| **API7: SSRF** | Source URLs validated against government domain allowlist |
| **API8: Misconfig** | Scoring weights in versioned config — not API-modifiable |
| **API9: Improper Inventory** | Scoring model versions tracked; A/B scoring for model transitions |
| **API10: Unsafe Consumption** | NIM/Milvus responses validated; fallback scoring on timeout |
