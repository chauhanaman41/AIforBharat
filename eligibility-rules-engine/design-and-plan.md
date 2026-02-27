# Eligibility Rules Engine — Design & Plan

## 1. Purpose

The Eligibility Rules Engine is the **CRITICAL deterministic logic layer** of the AIforBharat platform. It evaluates citizen profiles against government scheme eligibility criteria using **hard-coded, auditable business rules** — NOT LLM inference. This is a hybrid engine: deterministic rules produce the eligibility verdict, while an LLM generates human-readable explanations of why a citizen qualifies or doesn't.

**Design Philosophy**: A citizen's eligibility determination must be **reproducible, explainable, and legally defensible**. No probabilistic model should ever make the final eligibility call.

```
RULE: If age > 60 AND income < ₹2,00,000/year → Eligible for Old Age Pension
LLM:  "You qualify for the Old Age Pension because you are 65 years old 
       and your annual income of ₹1,80,000 is below the ₹2,00,000 threshold."
```

---

## 2. Capabilities

| Capability | Description |
|---|---|
| **Deterministic Rule Evaluation** | Hard-coded boolean logic: `IF condition_set THEN eligible/not_eligible` |
| **Rule Versioning** | Every rule change tracked with effective dates, author, and reason |
| **Multi-Scheme Batch Evaluation** | Evaluate one citizen against ALL 1000+ schemes in < 500ms |
| **Explanation Generation** | LLM produces natural-language explanation of rule match (post-evaluation) |
| **Partial Match Scoring** | Score 0-100% for "almost eligible" cases with specific gap identification |
| **Rule Conflict Detection** | Flag contradictory rules across schemes (e.g., mutually exclusive criteria) |
| **Temporal Rules** | Support date-dependent eligibility (seasonal schemes, budget-year limits) |
| **Composite Relationships** | Handle AND/OR/NOT combinations and nested rule groups |
| **Audit Trail** | Every evaluation logged with rule version, input snapshot, and result |
| **Rule Hot-Reload** | Update rules without engine restart via configuration reload |

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   Eligibility Rules Engine                     │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                 Rule Evaluation Core                       │ │
│  │                                                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │ │
│  │  │ Rule       │  │ Rule       │  │ Conflict         │    │ │
│  │  │ Repository │  │ Evaluator  │  │ Detector         │    │ │
│  │  │            │  │            │  │                  │    │ │
│  │  │ YAML/JSON  │  │ Boolean    │  │ Mutual exclusion │    │ │
│  │  │ rule defs  │  │ logic tree │  │ dependency check │    │ │
│  │  │ versioned  │  │ engine     │  │                  │    │ │
│  │  └────────────┘  └────────────┘  └──────────────────┘    │ │
│  └──────────────────────────┬───────────────────────────────┘ │
│                             │                                  │
│  ┌──────────────────────────▼───────────────────────────────┐ │
│  │              Explanation Layer (LLM-Powered)               │ │
│  │                                                            │ │
│  │  Rule Result + User Data ──▶ Llama 3.1 8B (via NIM)      │ │
│  │                             ──▶ Human-readable explanation │ │
│  │                                                            │ │
│  │  "You are eligible because your age (65) exceeds the      │ │
│  │   minimum (60) and your income (₹1.8L) is below the      │ │
│  │   cap (₹2L) for the Old Age Pension scheme."              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Supporting Components                         │ │
│  │                                                            │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │ │
│  │  │ Partial  │  │ Batch    │  │ Audit    │  │ Rule     │ │ │
│  │  │ Match    │  │ Evaluator│  │ Logger   │  │ Admin    │ │ │
│  │  │ Scorer   │  │          │  │          │  │ UI       │ │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

CRITICAL SEPARATION:
  ┌────────────────────────┐     ┌────────────────────────┐
  │   DETERMINISTIC LAYER  │     │     LLM LAYER          │
  │                        │     │                        │
  │   Rules Engine         │────▶│   Explanation Engine   │
  │   (Python logic)       │     │   (Llama 3.1 8B)      │
  │                        │     │                        │
  │   ✓ Makes decisions    │     │   ✗ Never decides      │
  │   ✓ Auditable          │     │   ✓ Only explains      │
  │   ✓ Reproducible       │     │   ✓ Human-readable     │
  │   ✓ Legally defensible │     │   ✓ Multi-language     │
  └────────────────────────┘     └────────────────────────┘
```

---

## 4. Data Models

### 4.1 Rule Definition (YAML)

```yaml
# schemes/karnataka/old_age_pension.yaml
schema_version: "1.0"
rule_id: "rule_ka_oap_001"
scheme_id: "sch_ka_old_age_pension"
scheme_name: "Karnataka Old Age Pension"
state: "karnataka"
department: "social_welfare"
effective_from: "2024-04-01"
effective_until: null  # null = no expiry
version: 3
last_modified_by: "policy_sync_engine"
last_modified_at: "2025-01-10T08:00:00Z"

eligibility:
  operator: "AND"
  conditions:
    - field: "demographics.state"
      operator: "eq"
      value: "karnataka"
      label: "Must be Karnataka resident"
    
    - field: "identity.age"
      operator: "gte"
      value: 65
      label: "Must be 65 years or older"
    
    - field: "economic.annual_income"
      operator: "lte"
      value: 200000
      label: "Annual income must not exceed ₹2,00,000"
    
    - field: "economic.bpl_status"
      operator: "eq"
      value: true
      label: "Must be Below Poverty Line"
    
    - operator: "OR"
      conditions:
        - field: "identity.verified_documents"
          operator: "contains"
          value: "aadhaar"
          label: "Aadhaar verified"
        - field: "identity.verified_documents"
          operator: "contains"
          value: "voter_id"
          label: "Voter ID verified"

benefit:
  type: "monthly_pension"
  amount_inr: 2000
  disbursement: "direct_bank_transfer"
  frequency: "monthly"

exclusions:
  - field: "eligibility.active_schemes"
    operator: "not_contains"
    value: "sch_central_oap"
    label: "Must not be receiving Central Old Age Pension"

documents_required:
  - "aadhaar_card"
  - "income_certificate"
  - "age_proof"
  - "bpl_card"
  - "bank_passbook"

application:
  portal_url: "https://sevasindhu.karnataka.gov.in"
  deadline: null  # Open enrollment
  renewal_period_months: 12
```

### 4.2 Evaluation Result

```json
{
  "evaluation_id": "eval_uuid_v4",
  "user_id": "usr_123",
  "scheme_id": "sch_ka_old_age_pension",
  "rule_id": "rule_ka_oap_001",
  "rule_version": 3,
  "evaluated_at": "2025-01-15T10:30:00Z",
  
  "verdict": "ELIGIBLE",
  "match_score": 100,
  
  "conditions_evaluated": [
    {
      "field": "demographics.state",
      "operator": "eq",
      "expected": "karnataka",
      "actual": "karnataka",
      "result": true
    },
    {
      "field": "identity.age",
      "operator": "gte",
      "expected": 65,
      "actual": 68,
      "result": true
    },
    {
      "field": "economic.annual_income",
      "operator": "lte",
      "expected": 200000,
      "actual": 150000,
      "result": true,
      "headroom": 50000
    },
    {
      "field": "economic.bpl_status",
      "operator": "eq",
      "expected": true,
      "actual": true,
      "result": true
    }
  ],
  
  "exclusions_checked": [
    {
      "field": "eligibility.active_schemes",
      "check": "not_contains sch_central_oap",
      "result": true
    }
  ],
  
  "explanation": {
    "language": "en",
    "text": "You are eligible for the Karnataka Old Age Pension. You qualify because you are 68 years old (minimum: 65), your annual income of ₹1,50,000 is below the ₹2,00,000 threshold, and you hold a valid BPL card. Your estimated monthly benefit is ₹2,000 via direct bank transfer.",
    "generated_by": "llama-3.1-8b-instruct",
    "trust_score": 0.95
  },
  
  "benefit_estimate": {
    "monthly_inr": 2000,
    "annual_inr": 24000,
    "type": "direct_bank_transfer"
  },
  
  "next_steps": [
    "Apply at sevasindhu.karnataka.gov.in",
    "Upload Aadhaar card, income certificate, age proof, BPL card, bank passbook"
  ],
  
  "audit": {
    "input_snapshot_hash": "sha256_abc123",
    "rule_hash": "sha256_def456",
    "evaluation_duration_ms": 12,
    "explanation_duration_ms": 180
  }
}
```

### 4.3 Partial Match Result (Almost Eligible)

```json
{
  "verdict": "PARTIAL_MATCH",
  "match_score": 75,
  "matched_conditions": 3,
  "total_conditions": 4,
  
  "gaps": [
    {
      "field": "identity.age",
      "operator": "gte",
      "required": 65,
      "actual": 62,
      "gap": 3,
      "gap_description": "You are 3 years below the minimum age requirement",
      "estimated_eligibility_date": "2028-01-15"
    }
  ],
  
  "explanation": {
    "text": "You are not yet eligible for the Karnataka Old Age Pension. You meet 3 out of 4 requirements. You need to be at least 65 years old — you will become eligible around January 2028 when you turn 65. We will notify you when you become eligible."
  }
}
```

### 4.4 Rule Storage (PostgreSQL)

```sql
CREATE TABLE eligibility_rules (
    rule_id           VARCHAR(64) PRIMARY KEY,
    scheme_id         VARCHAR(64) NOT NULL,
    state             VARCHAR(32) NOT NULL,
    department        VARCHAR(64),
    rule_version      INTEGER NOT NULL DEFAULT 1,
    rule_definition   JSONB NOT NULL,      -- Full YAML-equivalent JSON
    rule_hash         VARCHAR(64) NOT NULL, -- SHA-256 of definition
    effective_from    DATE NOT NULL,
    effective_until   DATE,
    is_active         BOOLEAN DEFAULT true,
    created_by        VARCHAR(64) NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    supersedes        VARCHAR(64),          -- Previous version rule_id
    UNIQUE (scheme_id, rule_version)
);

CREATE TABLE evaluation_audit_log (
    evaluation_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL,
    scheme_id         VARCHAR(64) NOT NULL,
    rule_id           VARCHAR(64) NOT NULL,
    rule_version      INTEGER NOT NULL,
    input_hash        VARCHAR(64) NOT NULL,
    verdict           VARCHAR(20) NOT NULL,  -- ELIGIBLE, NOT_ELIGIBLE, PARTIAL_MATCH
    match_score       SMALLINT NOT NULL,
    conditions_result JSONB NOT NULL,
    evaluation_ms     INTEGER NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_eval_user ON evaluation_audit_log (user_id, created_at DESC);
CREATE INDEX idx_eval_scheme ON evaluation_audit_log (scheme_id, verdict);
```

---

## 5. Context Flow

```
Trigger: user.metadata.updated OR policy.rules.updated OR daily_batch_job

                    ┌──────────────────────┐
                    │ Processed User       │
                    │ Metadata Store       │
                    │                      │
                    │ age, income, state,  │
                    │ bpl, documents, etc. │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Rule Repository      │
                    │                      │
                    │ Load active rules    │
                    │ for user's state     │
                    │ + central schemes    │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────────────────┐
                    │ Batch Evaluator                   │
                    │                                   │
                    │ For each scheme_rule:             │
                    │   1. Extract required fields      │
                    │   2. Evaluate condition tree      │
                    │   3. Record per-condition result  │
                    │   4. Calculate match_score        │
                    │   5. Check exclusions             │
                    │   6. Determine verdict            │
                    └──────────┬───────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  ELIGIBLE    │  │  PARTIAL     │  │  NOT         │
    │  Schemes     │  │  MATCHES     │  │  ELIGIBLE    │
    │              │  │              │  │              │
    │  100% match  │  │  50-99%      │  │  < 50%       │
    │  No excl.    │  │  Gap ident.  │  │  Major gaps  │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                  │
           └─────────────────┼──────────────────┘
                             │
                    ┌────────▼──────────┐
                    │ Explanation Engine │
                    │ (Llama 3.1 8B)   │
                    │                   │
                    │ Generate human-   │
                    │ readable text for │
                    │ ELIGIBLE &        │
                    │ PARTIAL_MATCH     │
                    └────────┬──────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌──────────────┐ ┌────────────┐ ┌──────────────┐
    │ Event Bus    │ │ Audit Log  │ │ Cache        │
    │ (Kafka)      │ │ (Postgres) │ │ (Redis)      │
    │              │ │            │ │              │
    │ eligibility. │ │ Full eval  │ │ Result TTL:  │
    │ computed     │ │ record     │ │ 24h or until │
    │              │ │            │ │ data change  │
    └──────────────┘ └────────────┘ └──────────────┘
```

### Evaluation Logic (Python)

```python
from dataclasses import dataclass
from typing import Any
from enum import Enum

class Verdict(Enum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    PARTIAL_MATCH = "PARTIAL_MATCH"

@dataclass
class ConditionResult:
    field: str
    operator: str
    expected: Any
    actual: Any
    passed: bool
    headroom: Any = None  # How much margin above/below threshold

def evaluate_condition(condition: dict, user_data: dict) -> ConditionResult:
    """Evaluate a single condition against user data."""
    field_value = get_nested_field(user_data, condition['field'])
    expected = condition['value']
    op = condition['operator']
    
    passed = False
    headroom = None
    
    if op == 'eq':
        passed = field_value == expected
    elif op == 'gte':
        passed = field_value >= expected
        headroom = field_value - expected if isinstance(field_value, (int, float)) else None
    elif op == 'lte':
        passed = field_value <= expected
        headroom = expected - field_value if isinstance(field_value, (int, float)) else None
    elif op == 'contains':
        passed = expected in (field_value or [])
    elif op == 'not_contains':
        passed = expected not in (field_value or [])
    elif op == 'in':
        passed = field_value in expected
    elif op == 'between':
        passed = expected[0] <= field_value <= expected[1]
    
    return ConditionResult(
        field=condition['field'],
        operator=op,
        expected=expected,
        actual=field_value,
        passed=passed,
        headroom=headroom
    )

def evaluate_rule_tree(rule: dict, user_data: dict) -> tuple[bool, list[ConditionResult]]:
    """Recursively evaluate AND/OR condition trees."""
    results = []
    operator = rule.get('operator', 'AND')
    
    for condition in rule['conditions']:
        if 'conditions' in condition:  # Nested group
            nested_pass, nested_results = evaluate_rule_tree(condition, user_data)
            results.extend(nested_results)
        else:
            result = evaluate_condition(condition, user_data)
            results.append(result)
    
    if operator == 'AND':
        passed = all(r.passed for r in results)
    elif operator == 'OR':
        passed = any(r.passed for r in results)
    else:
        raise ValueError(f"Unknown operator: {operator}")
    
    return passed, results

def evaluate_eligibility(user_data: dict, rule_definition: dict) -> dict:
    """Full eligibility evaluation for one scheme."""
    passed, condition_results = evaluate_rule_tree(
        rule_definition['eligibility'], user_data
    )
    
    # Check exclusions
    exclusion_results = []
    excluded = False
    for excl in rule_definition.get('exclusions', []):
        excl_result = evaluate_condition(excl, user_data)
        exclusion_results.append(excl_result)
        if not excl_result.passed:
            excluded = True
    
    # Calculate match score
    total = len(condition_results)
    matched = sum(1 for r in condition_results if r.passed)
    match_score = int((matched / total) * 100) if total > 0 else 0
    
    # Determine verdict
    if passed and not excluded:
        verdict = Verdict.ELIGIBLE
    elif match_score >= 50:
        verdict = Verdict.PARTIAL_MATCH
    else:
        verdict = Verdict.NOT_ELIGIBLE
    
    return {
        'verdict': verdict.value,
        'match_score': match_score,
        'conditions': condition_results,
        'exclusions': exclusion_results,
        'gaps': [r for r in condition_results if not r.passed]
    }
```

---

## 6. Event Bus Integration

### Consumed Events

| Event | Source | Action |
|---|---|---|
| `user.metadata.updated` | Metadata Engine | Re-evaluate eligibility for user |
| `policy.rules.updated` | Government Data Sync Engine | Reload affected rules, re-evaluate affected users |
| `profile.assembled` | JSON User Info Generator | Batch re-evaluation if eligibility data stale |
| `scheme.deadline.approaching` | Deadline Monitoring Engine | Priority re-evaluation for expiring schemes |

### Published Events

| Event | Payload | Consumers |
|---|---|---|
| `eligibility.computed` | `{ user_id, scheme_id, verdict, match_score, benefit_estimate }` | JSON User Info Generator, Dashboard |
| `eligibility.batch.computed` | `{ user_id, total_eligible, total_partial, results[] }` | JSON User Info Generator, Analytics |
| `eligibility.new_match` | `{ user_id, scheme_id, scheme_name, benefit }` | Dashboard (toast notification) |
| `eligibility.lost` | `{ user_id, scheme_id, reason }` | Dashboard, Neural Network |
| `eligibility.partial_match` | `{ user_id, scheme_id, match_score, gaps[] }` | Dashboard (nudge), Neural Network |
| `rule.conflict.detected` | `{ rule_ids[], conflict_type, description }` | Admin, Anomaly Detection |

---

## 7. NVIDIA Stack Alignment

| NVIDIA Tool | Component | Usage |
|---|---|---|
| **NIM** | Explanation Engine | Llama 3.1 8B generates natural-language eligibility explanations |
| **TensorRT-LLM** | Explanation Optimization | Optimized inference for batch explanation generation |
| **NeMo BERT** | Rule Extraction | Extract structured rules from unstructured policy text (pipeline from Policy Fetching) |
| **Triton** | Model Serving | Serve BERT rule extractor and Llama explanation model |
| **RAPIDS cuDF** | Batch Evaluation | GPU-accelerated batch evaluation for millions of users |

### Explanation Generation Pipeline

```python
async def generate_explanation(
    evaluation: dict, 
    user_data: dict, 
    scheme: dict,
    language: str = "en"
) -> str:
    """Generate human-readable explanation using Llama 3.1 8B via NIM."""
    
    # Only generate explanations for ELIGIBLE and PARTIAL_MATCH
    if evaluation['verdict'] == 'NOT_ELIGIBLE' and evaluation['match_score'] < 50:
        return None
    
    prompt = f"""
    Generate a clear, simple explanation for an Indian citizen about their 
    eligibility for a government scheme.
    
    Scheme: {scheme['scheme_name']}
    Verdict: {evaluation['verdict']}
    Match Score: {evaluation['match_score']}%
    
    Conditions Met:
    {format_conditions(evaluation['conditions'], met=True)}
    
    Conditions Not Met:
    {format_conditions(evaluation['conditions'], met=False)}
    
    Benefit: {scheme['benefit']}
    
    Language: {language}
    
    Rules:
    - Use simple, non-technical language
    - Mention specific numbers (age, income) the citizen meets/misses
    - If partially eligible, explain what needs to change
    - Include estimated benefit amount
    - Do NOT make any eligibility determination — only explain the given verdict
    """
    
    response = await nim_client.generate(
        model="meta/llama-3.1-8b-instruct",
        prompt=prompt,
        max_tokens=200,
        temperature=0.2  # Low temperature for factual explanations
    )
    return response.text
```

---

## 8. Scaling Strategy

| Tier | Users | Strategy |
|---|---|---|
| **MVP** | < 10K | Single worker, ~100 rules, synchronous evaluation, Redis cache |
| **Growth** | 10K–500K | 3-5 workers partitioned by state, 500+ rules, async Kafka processing |
| **Scale** | 500K–5M | Worker pool with auto-scaling, RAPIDS GPU for batch evaluation, rule sharding by state |
| **Massive** | 5M–50M+ | Regional evaluation clusters, pre-computed eligibility matrices, incremental re-evaluation (only changed fields), RAPIDS multi-GPU batch |

### Evaluation Performance Targets

| Scenario | Users | Rules | Target |
|---|---|---|---|
| Single user, all schemes | 1 | 1,000 | < 500ms |
| Batch re-evaluation (rule change) | 100K | 1 | < 60 seconds |
| Nightly full re-evaluation | 1M | 1,000 | < 2 hours |
| Real-time single scheme | 1 | 1 | < 50ms |

### Caching Strategy

```
┌─────────────────────────────────────────────────────┐
│           Eligibility Cache (Redis)                  │
│                                                      │
│  Key: eligibility:{user_id}:{scheme_id}             │
│  Value: { verdict, match_score, explanation, ... }  │
│  TTL: 24 hours                                       │
│                                                      │
│  Invalidation triggers:                              │
│  - user.metadata.updated → invalidate user's cache  │
│  - policy.rules.updated → invalidate scheme's cache │
│  - Explicit re-evaluation request                    │
└─────────────────────────────────────────────────────┘
```

---

## 9. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/eligibility/{user_id}` | All eligibility results for user (cached) |
| `GET` | `/api/v1/eligibility/{user_id}/{scheme_id}` | Eligibility for specific scheme |
| `POST` | `/api/v1/eligibility/{user_id}/evaluate` | Force re-evaluation |
| `GET` | `/api/v1/eligibility/{user_id}/partial-matches` | Schemes where user is almost eligible |
| `GET` | `/api/v1/eligibility/{user_id}/gaps` | All eligibility gaps with remediation hints |
| `GET` | `/api/v1/rules/{scheme_id}` | Get rule definition (public, redacted) |
| `GET` | `/api/v1/rules/{scheme_id}/versions` | Rule version history |
| `POST` | `/api/v1/rules/validate` | Validate a rule definition (admin) |
| `POST` | `/api/v1/rules/simulate` | Simulate rule against sample population (admin) |
| `GET` | `/api/v1/rules/conflicts` | List detected rule conflicts |

---

## 10. Dependencies

### Upstream

| Engine | Data Provided |
|---|---|
| Processed User Metadata Store | Citizen demographics, economic data, family info |
| Identity Engine | Verified documents, age, identity status |
| Policy Fetching Engine | Raw policy text (for rule extraction pipeline) |
| Government Data Sync Engine | Rule updates, scheme amendments |

### Downstream

| Engine | Data Consumed |
|---|---|
| JSON User Info Generator | Eligibility results for profile assembly |
| Dashboard Interface | Eligibility cards, partial match nudges |
| Neural Network Engine | Eligibility context for AI recommendations |
| Deadline Monitoring Engine | Scheme deadlines for eligible schemes |
| Analytics Warehouse | Eligibility statistics for population analytics |
| Simulation Engine | Baseline eligibility for "what-if" scenarios |

---

## 11. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| Rule Format | YAML (authored) → JSON (runtime) |
| Rule Engine | Custom Python evaluator (no OPA dependency) |
| Cache | Redis 7.x (evaluation results) |
| Database | PostgreSQL 16 (rules + audit log) |
| Event Bus | Apache Kafka |
| Explanation LLM | Llama 3.1 8B via NVIDIA NIM |
| Batch Processing | RAPIDS cuDF (GPU batch evaluation) |
| Rule Validation | JSON Schema + custom validators |
| Monitoring | Prometheus + Grafana |
| Testing | pytest + hypothesis (property-based testing) |

---

## 12. Implementation Phases

### Phase 1 — Core Rule Engine (Weeks 1-2)
- Define YAML rule schema with JSON Schema validation
- Build recursive condition tree evaluator (AND/OR/NOT)
- Support operators: eq, gte, lte, contains, not_contains, in, between
- PostgreSQL rule storage with versioning
- Evaluation audit log

### Phase 2 — Batch & Integration (Weeks 3-4)
- Kafka consumer for user.metadata.updated
- Multi-scheme batch evaluation (1 user → all schemes)
- Partial match scoring with gap identification
- Redis caching with event-driven invalidation
- REST API endpoints

### Phase 3 — Explanation & Intelligence (Weeks 5-6)
- LLM explanation generation via NIM (Llama 3.1 8B)
- Multi-language explanation support (Hindi, English, regional)
- Rule conflict detection algorithm
- Rule hot-reload without restart
- Admin rule simulation endpoint

### Phase 4 — Scale (Weeks 7-8)
- RAPIDS GPU batch evaluation pipeline
- Incremental re-evaluation (only changed fields)
- Property-based testing with hypothesis
- Performance benchmarking: 1M users × 1000 rules < 2 hours
- Rule extraction from policy text via NeMo BERT (experimental)

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Single-user evaluation latency (all schemes) | < 500ms |
| Single-scheme evaluation latency | < 50ms |
| Evaluation accuracy (vs manual audit) | 100% (deterministic) |
| Explanation generation latency | < 300ms |
| Rule coverage (schemes with active rules) | > 90% of tracked schemes |
| Partial match identification rate | > 95% |
| Cache hit ratio | > 80% |
| Rule conflict detection | 100% of known conflict patterns |
| Audit log completeness | 100% of evaluations logged |
| Batch re-evaluation throughput | > 10K evaluations/sec |

---

## 14. Design Decisions

### Why NOT Use an LLM for Eligibility Decisions?

| Factor | LLM-Based | Rule Engine (Chosen) |
|---|---|---|
| **Reproducibility** | Non-deterministic | 100% reproducible |
| **Auditability** | Black box | Every condition traced |
| **Legal defensibility** | Cannot explain to court | Full rule chain audit |
| **Hallucination risk** | May fabricate eligibility | Zero — boolean logic |
| **Speed** | 500ms+ per scheme | < 1ms per scheme |
| **Cost** | GPU per evaluation | CPU only (no GPU needed for rules) |

### Hybrid Approach Rationale

The LLM is used **exclusively** for explanation generation — converting the deterministic result into human-readable language. The rule evaluation itself is pure Python boolean logic with zero ML dependencies. This ensures:

1. **Citizens can trust the system** — eligibility is never a probability
2. **Government can audit the system** — every rule is traceable
3. **Developers can test the system** — deterministic = fully testable
4. **The system scales cheaply** — rules run on CPU, LLM only for UI text

---

## 15. Official Data Sources (MVP)

| Data Required | Official Source | URL | Notes |
|---|---|---|---|
| Scheme eligibility criteria, scheme metadata | Open Government Data Portal | https://data.gov.in | Structured CSV/JSON scheme datasets |
| Scheme guidelines (PDF), detailed criteria | Respective Ministry Websites | https://www.india.gov.in | Manual extraction from PDFs may be required |
| State-specific scheme rules | State Govt Portals | https://www.india.gov.in/states | Select individual state — rules vary by state |
| Acts & amendments defining eligibility thresholds | India Code | https://www.indiacode.nic.in | Legal text for threshold values |
| Gazette rule changes affecting eligibility | eGazette | https://egazette.nic.in | Amendment notifications |

### Rule Extraction Pipeline

```
data.gov.in (structured) ──┐
Ministry PDFs (manual)  ────┤──▶ Rule Authoring (YAML) ──▶ Rule Engine
Gazette amendments       ───┘
```

---

## 16. Security Hardening

### 16.1 Rate Limiting

<!-- SECURITY: Eligibility endpoints are computationally expensive (batch evaluation against 1000+ rules).
     Rate limits prevent DoS via repeated batch evaluations.
     OWASP Reference: API4:2023 Unrestricted Resource Consumption -->

```yaml
rate_limits:
  # SECURITY: Single-scheme eligibility check
  "/api/v1/eligibility/check":
    per_user:
      requests_per_minute: 30
      burst: 10
    per_ip:
      requests_per_minute: 20

  # SECURITY: Batch evaluation (all 1000+ schemes) — expensive operation
  "/api/v1/eligibility/batch":
    per_user:
      requests_per_minute: 5
      burst: 2
    per_ip:
      requests_per_minute: 3

  # SECURITY: Rule admin endpoints — admin-only
  "/api/v1/rules/admin/*":
    per_user:
      requests_per_minute: 10
    require_role: admin
    ip_whitelist: ["10.0.0.0/8"]  # Internal network only

  # SECURITY: Explanation generation — LLM-powered, GPU-intensive
  "/api/v1/eligibility/explain":
    per_user:
      requests_per_minute: 15
      burst: 5

  rate_limit_response:
    status: 429
    headers:
      Retry-After: "<seconds>"
    body:
      error: "rate_limit_exceeded"
      message: "Eligibility evaluation rate limit reached. Please retry shortly."
```

### 16.2 Input Validation & Sanitization

<!-- SECURITY: User metadata inputs to rule evaluation must be strictly typed.
     Prevents rule injection, type confusion, and logic bypass.
     OWASP Reference: API3:2023, API8:2023 -->

```python
# SECURITY: Eligibility check request — strict schema, no extra fields
ELIGIBILITY_CHECK_SCHEMA = {
    "type": "object",
    "required": ["user_id", "scheme_id"],
    "additionalProperties": False,
    "properties": {
        "user_id": {
            "type": "string",
            "format": "uuid"  # Must be valid UUID
        },
        "scheme_id": {
            "type": "string",
            "pattern": "^sch_[a-zA-Z0-9_]{3,64}$"  # Strict scheme ID format
        },
        "language": {
            "type": "string",
            "enum": ["en", "hi", "bn", "te", "mr", "ta", "gu", "kn", "ml", "pa", "or", "ur"]
        },
        "include_explanation": {
            "type": "boolean"
        }
    }
}

# SECURITY: Rule definition validation — prevent code injection in YAML rules
RULE_DEFINITION_VALIDATORS = {
    "operators": ["eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in",
                  "contains", "not_contains", "between", "AND", "OR", "NOT"],
    "field_whitelist": [
        "demographics.state", "demographics.district", "demographics.urban_rural",
        "identity.age", "identity.gender", "identity.marital_status",
        "identity.verified_documents", "identity.social_category",
        "economic.annual_income", "economic.bpl_status", "economic.land_holding",
        "economic.employer_type", "economic.ration_card_type",
        "family.dependents_count", "family.children_count", "family.family_size",
        "eligibility.active_schemes"
    ],
    "max_conditions_per_rule": 50,  # Prevent overly complex rules
    "max_nesting_depth": 5,          # Prevent deeply nested logic bombs
    "value_constraints": {
        "string_max_length": 256,
        "number_min": -1000000000,
        "number_max": 1000000000,
        "array_max_items": 100
    }
}

# SECURITY: Sanitize LLM explanation prompts — prevent prompt injection
def sanitize_explanation_context(user_data: dict, rule_result: dict) -> dict:
    """Strip any user-controlled content that could be prompt injection."""
    sanitized = {}
    for key, value in user_data.items():
        if isinstance(value, str):
            # Remove potential prompt injection patterns
            value = re.sub(r'(ignore|forget|disregard)\s+(previous|above|all)', '', value, flags=re.I)
            value = value[:256]  # Truncate long strings
        sanitized[key] = value
    return sanitized
```

### 16.3 Secure API Key & Secret Management

<!-- SECURITY: Rule engine accesses user metadata and LLM services — all credentials
     are environment-sourced.
     OWASP Reference: API1:2023 -->

```yaml
secrets_management:
  environment_variables:
    - DB_PASSWORD               # PostgreSQL (rule store + evaluation audit)
    - REDIS_PASSWORD            # Evaluation result cache
    - KAFKA_SASL_PASSWORD       # Event bus auth
    - NIM_API_KEY               # NVIDIA NIM for Llama 3.1 explanation generation
    - TRITON_AUTH_TOKEN         # Triton inference server auth
    - METADATA_STORE_API_KEY    # Internal service-to-service auth

  rotation_policy:
    db_credentials: 90_days
    nim_api_key: 180_days
    service_tokens: 90_days

  # SECURITY: Never expose rule definitions or user data in error responses
  error_response_policy:
    include_rule_details: false  # Don't leak rule logic in errors
    include_user_data: false     # Don't echo user metadata in errors
    include_stack_trace: false   # Never in production
```

### 16.4 OWASP Compliance

| OWASP Risk | Mitigation |
|---|---|
| **API1: BOLA** | Users can only query their own eligibility; admin role required for cross-user queries |
| **API2: Broken Auth** | JWT validation on all endpoints; evaluation audit linked to authenticated user |
| **API3: Broken Property Auth** | Strict schema with `additionalProperties: false`; field whitelist for rule evaluation |
| **API4: Resource Consumption** | Batch evaluation capped at 5 req/min; max 50 conditions per rule |
| **API5: Broken Function Auth** | Rule admin (CRUD) restricted to admin role + internal network |
| **API6: Sensitive Flows** | Rule changes require version tracking, author attribution, and human review flag |
| **API7: SSRF** | No user-controlled URLs; LLM prompts sanitized against prompt injection |
| **API8: Misconfig** | Rule definitions validated against operator/field whitelists; no eval() or exec() |
| **API9: Improper Inventory** | Rule versioning with effective dates; deprecated rules archived |
| **API10: Unsafe Consumption** | NIM/Triton responses validated; timeouts enforced on LLM calls |
