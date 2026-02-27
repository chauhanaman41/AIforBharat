# Simulation Engine — Design & Plan

## 1. Purpose

The Simulation Engine powers the **"What if?" experience** — allowing citizens to explore hypothetical life changes and instantly see the civic, financial, and scheme eligibility impact. Questions like *"What if I move to Karnataka?"*, *"What if my income increases to ₹12L?"*, or *"What if I have another child?"* are answered with concrete, quantified projections: tax impact, subsidy changes, new scheme eligibility, benefit gains/losses, and recommended actions.

This engine does NOT modify real data. It creates **ephemeral simulation contexts** — cloned user profiles with modified parameters — and runs them through the Eligibility Rules Engine, tax calculators, and RAPIDS impact models to produce side-by-side comparisons.

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Life Event Simulation** | Model state changes: relocation, income change, marriage, child birth, retirement |
| **Tax Impact Projection** | Compare old vs new regime, calculate effective tax after event |
| **Scheme Eligibility Delta** | Show gained/lost scheme eligibility after simulated change |
| **Subsidy Impact** | Calculate subsidy changes (LPG, electricity, ration, housing) |
| **Benefit Projection** | Estimate total annual benefit change (₹ gained vs ₹ lost) |
| **Multi-Variable Simulation** | Combine changes: "Move to Karnataka AND income becomes ₹15L" |
| **Time-Series Projection** | Project impact over 1/3/5 years with trend modeling |
| **Comparison Dashboard** | Side-by-side: current state vs simulated state |
| **Scenario Bookmarking** | Save and revisit simulation scenarios |
| **Crowd-Sourced Scenarios** | Popular "what-if" templates based on common life transitions |

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Simulation Engine                        │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │               Simulation Controller                        │ │
│  │                                                            │ │
│  │  1. Receive simulation parameters                         │ │
│  │  2. Clone user profile (ephemeral)                        │ │
│  │  3. Apply parameter mutations                             │ │
│  │  4. Route to computation engines                          │ │
│  │  5. Aggregate results                                     │ │
│  │  6. Generate comparison report                            │ │
│  └──────────────────────────┬───────────────────────────────┘ │
│                             │                                  │
│  ┌──────────────────────────▼───────────────────────────────┐ │
│  │               Computation Engines                          │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │ │
│  │  │ Eligibility│  │ Tax        │  │ Impact           │    │ │
│  │  │ Simulator  │  │ Calculator │  │ Modeler          │    │ │
│  │  │            │  │            │  │                  │    │ │
│  │  │ Re-run     │  │ Old vs new │  │ RAPIDS XGBoost   │    │ │
│  │  │ rules on   │  │ regime     │  │ time-series      │    │ │
│  │  │ mutated    │  │ comparison │  │ projection       │    │ │
│  │  │ profile    │  │            │  │                  │    │ │
│  │  └────────────┘  └────────────┘  └──────────────────┘    │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐                           │ │
│  │  │ Subsidy    │  │ NLP        │                           │ │
│  │  │ Calculator │  │ Summary    │                           │ │
│  │  │            │  │ Generator  │                           │ │
│  │  │ LPG, elec, │  │            │                           │ │
│  │  │ ration     │  │ Llama 3.1  │                           │ │
│  │  └────────────┘  └────────────┘                           │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │               Result Layer                                 │ │
│  │                                                            │ │
│  │  ┌────────────────┐  ┌────────────┐  ┌────────────────┐  │ │
│  │  │ Comparison     │  │ Scenario   │  │ Cache          │  │ │
│  │  │ Report         │  │ Bookmarks  │  │ (Redis)        │  │ │
│  │  │ (Delta view)   │  │ (Postgres) │  │ TTL: 30 min    │  │ │
│  │  └────────────────┘  └────────────┘  └────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Data Models

### 4.1 Simulation Request

```json
{
  "simulation_id": "sim_uuid_v4",
  "user_id": "usr_123",
  "requested_at": "2025-01-15T10:30:00Z",
  
  "parameters": [
    {
      "field": "demographics.state",
      "current_value": "maharashtra",
      "simulated_value": "karnataka",
      "label": "Relocate to Karnataka"
    },
    {
      "field": "economic.annual_income",
      "current_value": 800000,
      "simulated_value": 1200000,
      "label": "Income increases to ₹12L"
    }
  ],
  
  "options": {
    "include_tax_comparison": true,
    "include_subsidy_impact": true,
    "include_time_projection": true,
    "projection_years": 3,
    "language": "en"
  }
}
```

### 4.2 Simulation Result

```json
{
  "simulation_id": "sim_uuid_v4",
  "user_id": "usr_123",
  "computed_at": "2025-01-15T10:30:02Z",
  "computation_time_ms": 1850,
  
  "summary": {
    "net_annual_impact_inr": -35000,
    "impact_direction": "negative",
    "headline": "Moving to Karnataka with higher income reduces your net benefits by approximately ₹35,000/year, mainly due to lost Maharashtra-specific schemes, but you gain eligibility for 3 new Karnataka schemes."
  },
  
  "eligibility_delta": {
    "schemes_gained": [
      {
        "scheme_id": "sch_ka_001",
        "scheme_name": "Karnataka Housing Scheme",
        "annual_benefit_inr": 50000,
        "confidence": 0.92
      }
    ],
    "schemes_lost": [
      {
        "scheme_id": "sch_mh_001",
        "scheme_name": "Maharashtra Employment Guarantee",
        "annual_benefit_inr": 72000,
        "reason": "State residency requirement"
      }
    ],
    "schemes_unchanged": 8,
    "net_eligible_change": -2,
    "net_benefit_change_inr": -22000
  },
  
  "tax_comparison": {
    "current": {
      "regime": "new",
      "gross_income": 800000,
      "taxable_income": 650000,
      "tax_liability": 32500,
      "effective_rate_pct": 4.06
    },
    "simulated": {
      "regime": "new",
      "gross_income": 1200000,
      "taxable_income": 1050000,
      "tax_liability": 82500,
      "effective_rate_pct": 6.88
    },
    "delta": {
      "additional_tax_inr": 50000,
      "rate_change_pct": 2.82,
      "recommendation": "Consider old regime — potential savings of ₹15,000 with 80C deductions"
    }
  },
  
  "subsidy_impact": {
    "lpg_subsidy": { "current": 200, "simulated": 0, "change": -200, "reason": "Income above ₹10L threshold" },
    "electricity_subsidy": { "current": 0, "simulated": 0, "change": 0 },
    "ration_card": { "current": "APL", "simulated": "APL", "change": "no_change" }
  },
  
  "time_projection": {
    "years": [
      {
        "year": 2025,
        "net_benefit_current_inr": 145000,
        "net_benefit_simulated_inr": 110000,
        "cumulative_delta_inr": -35000
      },
      {
        "year": 2026,
        "net_benefit_current_inr": 148000,
        "net_benefit_simulated_inr": 118000,
        "cumulative_delta_inr": -65000
      },
      {
        "year": 2027,
        "net_benefit_current_inr": 151000,
        "net_benefit_simulated_inr": 125000,
        "cumulative_delta_inr": -91000
      }
    ]
  },
  
  "recommendations": [
    "Apply for Karnataka Housing Scheme before relocating — you can start the process now",
    "Consider maximizing 80C deductions if switching to old tax regime at higher income",
    "Transfer PM-KISAN registration to Karnataka after establishing residency"
  ],
  
  "trust": {
    "overall_confidence": "medium",
    "tax_confidence": "high",
    "eligibility_confidence": "medium",
    "projection_confidence": "low",
    "disclaimer": "Projections are estimates based on current policy. Actual outcomes may vary."
  }
}
```

### 4.3 Scenario Templates

```json
{
  "template_id": "tmpl_relocation",
  "name": "State Relocation",
  "description": "See how moving to another state affects your benefits",
  "popularity_rank": 1,
  "parameters": [
    {
      "field": "demographics.state",
      "input_type": "dropdown",
      "options_source": "indian_states",
      "label": "Which state are you considering?"
    },
    {
      "field": "demographics.urban_rural",
      "input_type": "toggle",
      "options": ["urban", "rural"],
      "label": "Urban or rural area?"
    }
  ],
  "tags": ["relocation", "migration", "state_change"]
}
```

---

## 5. Context Flow

```
User Dashboard
  │
  │  "What if I move to Karnataka and my income becomes ₹12L?"
  │
  ▼
┌────────────────────────────────┐
│   Simulation Controller        │
│                                │
│  1. Parse parameters           │
│  2. Fetch current profile      │
│     from JSON User Info Gen    │
│  3. Clone profile (in-memory)  │
│  4. Apply mutations:           │
│     state: MH → KA            │
│     income: 8L → 12L          │
└──────────────┬─────────────────┘
               │
    ┌──────────┼──────────┬──────────────┐
    ▼          ▼          ▼              ▼
┌────────┐ ┌────────┐ ┌────────┐  ┌──────────┐
│Elig.   │ │Tax     │ │Subsidy │  │Impact    │
│Rules   │ │Calc    │ │Calc    │  │Modeler   │
│Engine  │ │        │ │        │  │(RAPIDS)  │
│        │ │        │ │        │  │          │
│Evaluate│ │Compare │ │Check   │  │XGBoost   │
│mutated │ │old/new │ │income  │  │time-     │
│profile │ │regime  │ │thresh- │  │series    │
│vs all  │ │        │ │olds    │  │projection│
│schemes │ │        │ │        │  │          │
└──┬─────┘ └──┬─────┘ └──┬─────┘  └──┬───────┘
   │          │          │           │
   └──────────┴──────────┴───────────┘
                    │
         ┌──────────▼──────────┐
         │ Result Aggregator    │
         │                     │
         │ Compute deltas:     │
         │ - Eligibility diff  │
         │ - Tax diff          │
         │ - Subsidy diff      │
         │ - Net impact ₹      │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │ NLP Summary (NIM)   │
         │                     │
         │ Generate human-     │
         │ readable headline   │
         │ and recommendations │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │ Response + Cache    │
         │                     │
         │ Cache: 30 min       │
         │ Bookmark: persist   │
         └─────────────────────┘
```

---

## 6. Event Bus Integration

### Consumed Events

| Event | Source | Action |
|---|---|---|
| `user.simulation.requested` | Dashboard Interface | Trigger simulation computation |
| `profile.assembled` | JSON User Info Generator | Refresh baseline profile for simulations |
| `eligibility.rules.updated` | Eligibility Rules Engine | Invalidate cached simulations |
| `tax.rules.updated` | Government Data Sync Engine | Update tax calculation models |

### Published Events

| Event | Payload | Consumers |
|---|---|---|
| `simulation.result.ready` | `{ simulation_id, user_id, net_impact_inr, headline }` | Dashboard Interface |
| `simulation.popular_scenario` | `{ template_id, usage_count }` | Analytics Warehouse |
| `simulation.insight.generated` | `{ user_id, insight_type, recommendation }` | Neural Network Engine |

---

## 7. NVIDIA Stack Alignment

| NVIDIA Tool | Component | Usage |
|---|---|---|
| **RAPIDS cuDF** | Data Transformation | GPU-accelerated profile mutation and feature engineering |
| **RAPIDS XGBoost** | Impact Modeling | GPU-accelerated time-series benefit projection |
| **NeMo Transformer** | Time-Series Forecasting | Transformer model for long-term benefit trend prediction |
| **NIM** | Summary Generation | Llama 3.1 8B generates human-readable impact summaries |
| **TensorRT-LLM** | Fast Inference | Optimized summary generation for real-time simulation feedback |
| **Triton** | Model Serving | Serve XGBoost impact model and NeMo forecaster |

### RAPIDS Time-Series Projection

```python
import cudf
import cupy as cp
from xgboost import XGBRegressor

class ImpactProjector:
    """GPU-accelerated benefit projection using RAPIDS + XGBoost."""
    
    def __init__(self, model_path: str):
        self.model = XGBRegressor()
        self.model.load_model(model_path)
    
    def project_benefits(
        self,
        current_profile: dict,
        simulated_profile: dict,
        years: int = 3
    ) -> list[dict]:
        """Project annual benefits for both current and simulated profiles."""
        
        projections = []
        for year_offset in range(years):
            # Age each profile forward
            current_features = self._extract_features(current_profile, year_offset)
            simulated_features = self._extract_features(simulated_profile, year_offset)
            
            # GPU prediction
            current_gdf = cudf.DataFrame([current_features])
            simulated_gdf = cudf.DataFrame([simulated_features])
            
            current_benefit = float(self.model.predict(current_gdf)[0])
            simulated_benefit = float(self.model.predict(simulated_gdf)[0])
            
            projections.append({
                "year": 2025 + year_offset,
                "net_benefit_current_inr": round(current_benefit),
                "net_benefit_simulated_inr": round(simulated_benefit),
                "delta_inr": round(simulated_benefit - current_benefit)
            })
        
        return projections
    
    def _extract_features(self, profile: dict, year_offset: int) -> dict:
        """Extract model features with temporal aging."""
        age = profile.get('identity', {}).get('age', 30) + year_offset
        return {
            'age': age,
            'income': profile['economic']['annual_income'] * (1.05 ** year_offset),
            'state_encoded': self._encode_state(profile['demographics']['state']),
            'urban_rural': 1 if profile['demographics']['urban_rural'] == 'urban' else 0,
            'employment_encoded': self._encode_employment(profile['economic']['employment_type']),
            'dependents': profile.get('family', {}).get('dependents', 0),
            'year_offset': year_offset
        }
```

### Indian Tax Calculator

```python
def calculate_income_tax(income: float, regime: str = "new", deductions: dict = None) -> dict:
    """Calculate Indian income tax under old/new regime (FY 2024-25)."""
    
    if regime == "new":
        slabs = [
            (300000, 0.00),
            (700000, 0.05),
            (1000000, 0.10),
            (1200000, 0.15),
            (1500000, 0.20),
            (float('inf'), 0.30)
        ]
        standard_deduction = 75000
        taxable = max(0, income - standard_deduction)
    else:
        slabs = [
            (250000, 0.00),
            (500000, 0.05),
            (1000000, 0.20),
            (float('inf'), 0.30)
        ]
        total_deductions = sum((deductions or {}).values())
        standard_deduction = 50000
        taxable = max(0, income - standard_deduction - total_deductions)
    
    tax = 0
    prev_limit = 0
    for limit, rate in slabs:
        if taxable <= 0:
            break
        taxable_in_slab = min(taxable, limit - prev_limit)
        tax += taxable_in_slab * rate
        taxable -= taxable_in_slab
        prev_limit = limit
    
    # Section 87A rebate (new regime: income <= 7L)
    if regime == "new" and income <= 700000:
        tax = 0
    
    cess = tax * 0.04  # Health & Education Cess
    total_tax = tax + cess
    
    return {
        "regime": regime,
        "gross_income": income,
        "taxable_income": max(0, income - standard_deduction - sum((deductions or {}).values())),
        "tax_before_cess": round(tax),
        "cess": round(cess),
        "total_tax": round(total_tax),
        "effective_rate_pct": round((total_tax / income) * 100, 2) if income > 0 else 0
    }
```

---

## 8. Scaling Strategy

| Tier | Users | Strategy |
|---|---|---|
| **MVP** | < 10K | Synchronous simulation, single worker, Redis result cache |
| **Growth** | 10K–500K | Async simulation via Kafka, 3-5 workers, pre-computed popular scenarios |
| **Scale** | 500K–5M | RAPIDS GPU acceleration, scenario template caching, worker auto-scaling |
| **Massive** | 5M–50M+ | Pre-computed scenario matrices for common state×income combinations, RAPIDS multi-GPU, CDN-cached popular results |

---

## 9. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/simulate` | Run a new simulation |
| `GET` | `/api/v1/simulate/{simulation_id}` | Get simulation result |
| `GET` | `/api/v1/simulate/templates` | List scenario templates |
| `POST` | `/api/v1/simulate/tax-compare` | Compare old vs new tax regime |
| `POST` | `/api/v1/simulate/{simulation_id}/bookmark` | Save scenario |
| `GET` | `/api/v1/simulate/bookmarks/{user_id}` | Get saved scenarios |
| `GET` | `/api/v1/simulate/popular` | Popular scenarios across platform |

---

## 10. Dependencies

### Upstream

| Engine | Data Provided |
|---|---|
| JSON User Info Generator | Baseline profile for cloning |
| Eligibility Rules Engine | Re-evaluation on mutated profiles |
| Analytics Warehouse | Historical benefit data for projection models |
| Government Data Sync Engine | Current tax rules and subsidy thresholds |

### Downstream

| Engine | Data Consumed |
|---|---|
| Dashboard Interface | Simulation results for slider widget |
| Neural Network Engine | Simulation insights for recommendations |
| Analytics Warehouse | Popular scenario telemetry |

---

## 11. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| GPU Compute | RAPIDS cuDF + XGBoost (GPU) |
| Time-Series Model | NeMo Transformer (optional) |
| Tax Calculator | Custom Python module |
| Cache | Redis 7.x (simulation results, TTL: 30 min) |
| Database | PostgreSQL 16 (scenario bookmarks) |
| Event Bus | Apache Kafka |
| NLP Summary | NVIDIA NIM (Llama 3.1 8B) |
| Model Serving | Triton Inference Server |
| Monitoring | Prometheus + Grafana |

---

## 12. Implementation Phases

### Phase 1 — Core Simulation (Weeks 1-3)
- Profile cloning and parameter mutation engine
- Integration with Eligibility Rules Engine for re-evaluation
- Basic tax calculator (old vs new regime, FY 2024-25)
- Side-by-side eligibility comparison
- REST API endpoints

### Phase 2 — Financial Modeling (Weeks 4-5)
- Subsidy impact calculator (LPG, electricity, ration)
- Multi-variable simulation support
- Scenario templates for common life events
- Result caching in Redis

### Phase 3 — GPU Projections (Weeks 6-7)
- RAPIDS XGBoost time-series projection model
- Training pipeline on historical benefit data
- NIM-powered natural-language summary generation
- Scenario bookmarking

### Phase 4 — Scale & Intelligence (Weeks 8-9)
- Pre-computed scenario matrices for popular combinations
- NeMo Transformer for long-term forecasting
- Worker auto-scaling on simulation queue depth
- Performance target: < 2 seconds p95 for standard simulation

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Simulation latency (p50) | < 1.5 seconds |
| Simulation latency (p95) | < 3 seconds |
| Tax calculation accuracy | 100% (deterministic) |
| Eligibility delta accuracy | 100% (re-uses Rules Engine) |
| Projection confidence (1-year) | > 80% |
| Projection confidence (3-year) | > 60% |
| Cache hit ratio (popular scenarios) | > 40% |
| User engagement (simulations per user/month) | > 2 |
| Scenario completion rate | > 70% |
| NLP summary quality (user rating) | > 4.0/5.0 |

---

## 14. Official Data Sources — Financial & Simulation (MVP)

| Data Required | Official Source | URL | Notes |
|---|---|---|---|
| Tax slabs, official slab tables | Income Tax India | https://www.incometax.gov.in | Old vs new regime rates, deductions, exemptions |
| Budget allocations, annual PDFs | Union Budget Portal | https://www.indiabudget.gov.in | Scheme-wise fund allocation |
| Interest rates, repo rate, financial indicators | RBI DBIE | https://dbie.rbi.org.in | Database on Indian Economy |
| Inflation data, economic data | Reserve Bank of India | https://www.rbi.org.in | CPI, WPI, monetary policy data |

### Optional Future — Financial/Market Data

| Data | Source | URL | Notes |
|---|---|---|---|
| Stock data | NSE India | https://www.nseindia.com | Limited scraping — check ToS |
| Free stock API | Alpha Vantage | https://www.alphavantage.co | Free API key available |
| Market data | Yahoo Finance | https://finance.yahoo.com | Free via `yfinance` Python library |

### Usage in Simulation Engine

- **Income Tax Portal** → Tax calculator (old vs new regime comparison, Section 80C/80D)
- **Union Budget** → Scheme-level allocation for benefit projection accuracy
- **RBI DBIE** → Interest rate projections for loan/savings simulations
- **RBI Inflation** → Real-value adjustment for multi-year projections

---

## 16. Security Hardening

### 16.1 Rate Limiting

<!-- SECURITY: Simulations are compute-intensive (multi-engine evaluation + LLM summary).
     Rate limits prevent GPU/CPU exhaustion.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  # SECURITY: Single simulation — runs eligibility + tax + subsidy calculators
  "/api/v1/simulate":
    per_user:
      requests_per_minute: 10
      requests_per_hour: 60
      burst: 3
    per_ip:
      requests_per_minute: 5

  # SECURITY: Multi-variable simulation — exponentially more compute
  "/api/v1/simulate/multi":
    per_user:
      requests_per_minute: 5
      burst: 2

  # SECURITY: Time-series projection — RAPIDS GPU operation
  "/api/v1/simulate/project":
    per_user:
      requests_per_minute: 5
      burst: 2

  # SECURITY: Bookmarked scenarios — lightweight reads
  "/api/v1/simulate/bookmarks":
    per_user:
      requests_per_minute: 30

  rate_limit_response:
    status: 429
    body:
      error: "rate_limit_exceeded"
      message: "Simulation rate limit reached. Please wait before running another scenario."
    headers:
      Retry-After: "<seconds>"
```

### 16.2 Input Validation & Sanitization

<!-- SECURITY: Simulation parameters mutate user profiles (in-memory clones).
     Invalid inputs could cause logic errors or resource exhaustion.
     OWASP Reference: API3:2023, API8:2023 -->

```python
# SECURITY: Simulation request schema — strict parameter validation
SIMULATION_REQUEST_SCHEMA = {
    "type": "object",
    "required": ["parameters"],
    "additionalProperties": False,
    "properties": {
        "parameters": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,  # Max 5 simultaneous parameter changes
            "items": {
                "type": "object",
                "required": ["field", "simulated_value"],
                "additionalProperties": False,
                "properties": {
                    "field": {
                        "type": "string",
                        "enum": [
                            "demographics.state", "demographics.district",
                            "demographics.urban_rural",
                            "economic.annual_income", "economic.employer_type",
                            "economic.land_holding", "economic.bpl_status",
                            "family.dependents_count", "family.children_count",
                            "family.marital_status",
                            "identity.age", "identity.gender"
                        ]
                    },
                    "simulated_value": {
                        "oneOf": [
                            {"type": "string", "maxLength": 64},
                            {"type": "number", "minimum": 0, "maximum": 100000000},
                            {"type": "boolean"},
                            {"type": "integer", "minimum": 0, "maximum": 200}
                        ]
                    }
                }
            }
        },
        "options": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "include_tax_comparison": {"type": "boolean"},
                "include_subsidy_impact": {"type": "boolean"},
                "include_time_projection": {"type": "boolean"},
                "projection_years": {"type": "integer", "minimum": 1, "maximum": 10},
                "language": {
                    "type": "string",
                    "enum": ["en", "hi", "bn", "te", "mr", "ta", "gu", "kn"]
                }
            }
        }
    }
}

# SECURITY: Validate simulation value ranges against field type
FIELD_VALUE_CONSTRAINTS = {
    "demographics.state": {"type": "string", "enum": ["AP","AR","AS","BR","CG","GA","GJ","HR","HP","JH","KA","KL","MP","MH","MN","ML","MZ","NL","OD","PB","RJ","SK","TN","TS","TR","UP","UK","WB"]},
    "economic.annual_income": {"type": "number", "min": 0, "max": 100000000},
    "identity.age": {"type": "integer", "min": 0, "max": 150},
    "family.dependents_count": {"type": "integer", "min": 0, "max": 20},
}

# SECURITY: Simulation results always include disclaimer
DISCLAIMER = "Simulation based on current policy data. Actual outcomes may vary. This is not legal or financial advice."
```

### 16.3 Secure API Key & Secret Management

```yaml
secrets_management:
  environment_variables:
    - DB_PASSWORD               # PostgreSQL (scenario bookmarks)
    - REDIS_PASSWORD            # Simulation result cache
    - KAFKA_SASL_PASSWORD       # Event bus auth
    - NIM_API_KEY               # NLP summary generation via Llama 3.1
    - ELIGIBILITY_SERVICE_TOKEN # Internal service-to-service auth
    - METADATA_SERVICE_TOKEN    # User metadata service auth

  rotation_policy:
    db_credentials: 90_days
    service_tokens: 90_days
    nim_api_key: 180_days

  # SECURITY: Simulation results are ephemeral — no PII stored in results
  data_handling:
    clone_profiles_in_memory_only: true
    never_persist_simulated_pii: true
    cache_ttl_minutes: 30
```

### 16.4 OWASP Compliance

| OWASP Risk | Mitigation |
|---|---|
| **API1: BOLA** | Users can only simulate against their own profile; cross-user simulation requires admin |
| **API2: Broken Auth** | JWT validation; simulation results linked to authenticated user |
| **API3: Broken Property Auth** | `additionalProperties: false`; field enum whitelist prevents arbitrary mutations |
| **API4: Resource Consumption** | Max 5 params per simulation; projection capped at 10 years; rate limited |
| **API5: Broken Function Auth** | Admin-only endpoints for system-wide simulations |
| **API6: Sensitive Flows** | Simulated profiles never persisted; always ephemeral in-memory clones |
| **API7: SSRF** | No external URL inputs; all data from internal services only |
| **API8: Misconfig** | No eval() on simulation parameters; all mutations via switch-case logic |
| **API9: Improper Inventory** | Scenario templates versioned; deprecated templates flagged |
| **API10: Unsafe Consumption** | Eligibility/Tax engine responses validated; timeouts enforced |

---

## ⚙️ Build Phase Instructions (Current Phase Override)

> **These instructions override any conflicting guidance above for the current local build phase.**

### 1. Local-First Architecture
- Build and run this engine **entirely locally**. Do NOT integrate any AWS cloud services.
- Store all secrets in a local `.env` file.
- Run RAPIDS/XGBoost locally for simulation computations.

### 2. Data Storage & Caching (Zero-Redundancy)
- Before downloading or fetching any external data, **always check if the target data already exists locally**.
- If present locally → skip the download and load directly from the local path.
- Only download/fetch data if it is **completely missing locally**.
- **Local datasets available** (use these for tax/scheme simulation models):
  - Finance/economic data: `C:\Users\Amandeep\Downloads\financefiles\` (GDP, CPI, WPI, monetary policy rates, MSP, etc.)
  - Census 2011 PCA: `C:\Users\Amandeep\Downloads\DDW_PCA0000_2011_Indiastatedist.xlsx`
  - SDG India Index: `C:\Users\Amandeep\Downloads\amandeepsinghchauhan5_17722109276149728.csv`
  - Poverty data: `C:\Users\Amandeep\Downloads\amandeepsinghchauhan5_17722114987588584.csv`
- For tax data (incometax.gov.in, RBI): check local finance files first; only call APIs if specific data is missing.

### 3. Deferred Features (Do NOT Implement Yet)
- **Notifications & Messaging**: Do not build or integrate any notification systems.
- **External market data APIs** (NSE, Alpha Vantage, Yahoo Finance): Skip for now; use local finance data.

### 4. Primary Focus
Build a robust, locally-functioning simulation engine with:
- "What if?" tax and scheme impact projections
- Income change, family status change simulations
- Multi-year projection models
- Ephemeral in-memory simulation (no PII persistence)
- All functionality testable without any external service or cloud dependencies
