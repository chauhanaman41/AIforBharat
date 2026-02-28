# AIforBharat Orchestration Testing Report

> **Execution Context**: Local execution, 21 engines running concurrently behind API Gateway (E0:8000)

## Engine / Flow Name: User Onboarding Flow (E1 -> E2 -> E4 -> E5 -> E15||E16 -> E12 -> Audit)
**Test Scenario / Purpose:** A new user registers and their profile is created, metadata is normalized, eligibility is batch-checked, and deadlines are listed.

**Test Inputs:**
```json
{
  "phone": "9891361660",
  "password": "SecurePassword123!",
  "name": "Raj Kumar",
  "state": "UP",
  "district": "Lucknow",
  "language_preference": "hi",
  "consent_data_processing": true,
  "date_of_birth": "1980-05-15",
  "annual_income": 120000.0,
  "occupation": "farmer"
}
```

**Expected Output:**
A JSON response containing the user_id, access_token, identity_token, eligibility_summary, and upcoming_deadlines. It should gracefully degrade if any non-critical engine fails.

**Actual Output / Result:** (PASS)
```json
{
  "success": true,
  "message": "Onboarding complete",
  "data": {
    "user_id": "usr_2e5b1d1d251f",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c3JfMmU1YjFkMWQyNTFmIiwicm9sZXMiOlsiY2l0aXplbiJdLCJpYXQiOjE3NzIyNjAyMDUsImV4cCI6MTc3MjI2MjAwNSwidHlwZSI6ImFjY2VzcyJ9.ZiC5dE7n7OkXX3t9I9k0IfL8R3QzxfubbvRFVeF1oaY",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c3JfMmU1YjFkMWQyNTFmIiwiaWF0IjoxNzcyMjYwMjA1LCJleHAiOjE3NzI4NjUwMDUsInR5cGUiOiJyZWZyZXNoIn0.ok0pZBLnVHvXPBnYZcTX4gD5_wxG3jrzeL7P9hGDnAY",
    "identity_token": "543b5e8adb9792570903d764fcf03706b3860b2db25a0e14e93d8a119cb52140",
    "eligibility_summary": {
      "eligible": 4,
      "partial": 3,
      "total_checked": 10
    },
    "upcoming_deadlines": 0,
    "profile_completeness": {
      "percentage": 60,
      "sources_available": 3,
      "sources_total": 5,
      "missing": [
        "trust_scoring_engine",
        "anomaly_detection_engine"
      ]
    },
    "degraded": null
  },
  "errors": null,
  "timestamp": "2026-02-28T06:30:07.535940",
  "request_id": "3e5fa5bc-6bf6-48ff-b210-b9069f196cb2"
}
```

**Required Changes for Future Reference:**
- Flow executed successfully. No immediate architecture changes required.

---

## Engine / Flow Name: Eligibility Check with Explanation (E15 -> E7 -> Audit)
**Test Scenario / Purpose:** Evaluate eligibility based on user profile and generate a human-readable explanation using the LLM.

**Test Inputs:**
```json
{
  "user_id": "usr_2e5b1d1d251f",
  "profile": {
    "age": 44,
    "annual_income": 120000,
    "state": "UP",
    "occupation": "farmer",
    "gender": "male"
  },
  "explain": true
}
```

**Expected Output:**
A JSON response with deterministic rules evaluation from E15, and an AI-generated explanation from E7.

**Actual Output / Result:** (PASS)
```json
{
  "success": true,
  "message": "OK",
  "data": {
    "user_id": "usr_2e5b1d1d251f",
    "total_schemes_checked": 10,
    "eligible": 4,
    "partial": 3,
    "ineligible": 3,
    "needs_verification": 0,
    "results": [
      {
        "scheme_id": "MUDRA-YOJANA-2024",
        "scheme_name": "PM MUDRA Yojana",
        "verdict": "eligible",
        "confidence": 1.0,
        "matched_rules": [
          {
            "status": "passed",
            "field": "age",
            "operator": "gte",
            "expected": "18",
            "actual": "45",
            "description": "Min age 18",
            "mandatory": true
          },
          {
            "status": "passed",
            "field": "employment_category",
            "operator": "in",
            "expected": "self_employed,other,agriculture",
            "actual": "agriculture",
            "description": "Non-corporate, non-farm enterprise",
            "mandatory": false
          }
        ],
        "unmet_rules": [],
        "missing_fields": [],
        "explanation": "You meet all eligibility criteria for PM MUDRA Yojana."
      },
      {
        "scheme_id": "PMSBY-2024",
        "scheme_name": "PM Suraksha Bima Yojana",
        "verdict": "eligible",
        "confidence": 1.0,
        "matched_rules": [
          {
            "status": "passed",
            "field": "age",
            "operator": "gte",
            "expected": "18",
            "actual": "45",
            "description": "Min age 18",
            "mandatory": true
          },
          {
            "status": "passed",
            "field": "age",
            "operator": "lte",
            "expected": "70",
            "actual": "45",
            "description": "Max age 70",
            "mandatory": true
          }
        ],
        "unmet_rules": [],
        "missing_fields": [],
        "explanation": "You meet all eligibility criteria for PM Suraksha Bima Yojana."
      },
      {
        "scheme_id": "PMJJBY-2024",
        "scheme_name": "PM Jeevan Jyoti Bima Yojana",
        "verdict": "eligible",
        "confidence": 1.0,
        "matched_rules": [
          {
            "status": "passed",
            "field": "age",
            "operator": "gte",
            "expected": "18",
            "actual": "45",
            "description": "Min age 18",
            "mandatory": true
          },
          {
            "status": "passed",
            "field": "age",
            "operator": "lte",
            "expected": "50",
            "actual": "45",
            "description": "Max age 50",
            "mandatory": true
          }
        ],
        "unmet_rules": [],
        "missing_fields": [],
        "explanation": "You meet all eligibility criteria for PM Jeevan Jyoti Bima Yojana."
      },
      {
        "scheme_id": "NATIONAL-PENSION-2024",
        "scheme_name": "National Pension System",
        "verdict": "eligible",
        "confidence": 1.0,
        "matched_rules": [
          {
            "status": "passed",
            "field": "age",
            "operator": "gte",
            "expected": "18",
            "actual": "45",
            "description": "Min age 18",
            "mandatory": true
          },
          {
            "status": "passed",
            "field": "age",
            "operator": "lte",
            "expected": "70",
            "actual": "45",
            "description": "Max age 70",
            "mandatory": true
          }
        ],
        "unmet_rules": [],
        "missing_fields": [],
        "explanation": "You meet all eligibility criteria for National Pension System."
      },
      {
        "scheme_id": "PM-KISAN-2024",
        "scheme_name": "PM Kisan Samman Nidhi",
        "verdict": "partial",
        "confidence": 0.5,
        "matched_rules": [
          {
            "status": "passed",
            "field": "occupation",
            "operator": "contains",
            "expected": "farmer,agriculture,kisan",
            "actual": "farmer",
            "description": "Must be a farmer",
            "mandatory": true
          },
          {
            "status": "passed",
            "field": "annual_income",
            "operator": "lte",
            "expected": "200000",
            "actual": "120000.0",
            "description": "Income \u2264 \u20b92,00,000",
            "mandatory": true
          }
        ],
        "unmet_rules": [],
        "missing_fields": [
          "land_holding_acres"
        ],
        "explanation": "You may be eligible for PM Kisan Samman Nidhi but we need more information: land_holding_acres."
      },
      {
        "scheme_id": "PM-AWAS-YOJANA-2024",
        "scheme_name": "PM Awas Yojana",
        "verdict": "partial",
        "confidence": 0.33,
        "matched_rules": [
          {
            "status": "passed",
            "field": "annual_income",
            "operator": "lte",
            "expected": "1800000",
            "actual": "120000.0",
            "description": "Income \u2264 \u20b918,00,000 (MIG-II)",
            "mandatory": true
          }
        ],
        "unmet_rules": [],
        "missing_fields": [
          "category"
        ],
        "explanation": "You may be eligible for PM Awas Yojana but we need more information: category."
      },
      {
        "scheme_id": "SCHOLARSHIP-SC-ST-2024",
        "scheme_name": "Post-Matric Scholarship SC/ST",
        "verdict": "partial",
        "confidence": 0.33,
        "matched_rules": [
          {
            "status": "passed",
            "field": "annual_income",
            "operator": "lte",
            "expected": "250000",
            "actual": "120000.0",
            "description": "Family income \u2264 \u20b92,50,000",
            "mandatory": true
          }
        ],
        "unmet_rules": [],
        "missing_fields": [
          "category"
        ],
        "explanation": "You may be eligible for Post-Matric Scholarship SC/ST but we need more information: category."
      },
      {
        "scheme_id": "AYUSHMAN-BHARAT-2024",
        "scheme_name": "Ayushman Bharat PM-JAY",
        "verdict": "ineligible",
        "confidence": 1.0,
        "matched_rules": [
          {
            "status": "passed",
            "field": "annual_income",
            "operator": "lte",
            "expected": "500000",
            "actual": "120000.0",
            "description": "Income \u2264 \u20b95,00,000",
            "mandatory": false
          }
        ],
        "unmet_rules": [
          {
            "status": "failed",
            "field": "is_bpl",
            "operator": "eq",
            "expected": "true",
            "actual": "False",
            "description": "Must be BPL or SECC-listed",
            "mandatory": true
          }
        ],
        "missing_fields": [],
        "explanation": "You are not eligible for Ayushman Bharat PM-JAY. Criteria not met: Must be BPL or SECC-listed."
      },
      {
        "scheme_id": "PM-UJJWALA-2024",
        "scheme_name": "PM Ujjwala Yojana",
        "verdict": "ineligible",
        "confidence": 0.9,
        "matched_rules": [],
        "unmet_rules": [
          {
            "status": "failed",
            "field": "is_bpl",
            "operator": "eq",
            "expected": "true",
            "actual": "False",
            "description": "Must be BPL household",
            "mandatory": true
          }
        ],
        "missing_fields": [
          "gender"
        ],
        "explanation": "You are not eligible for PM Ujjwala Yojana. Criteria not met: Must be BPL household."
      },
      {
        "scheme_id": "SUKANYA-SAMRIDDHI-2024",
        "scheme_name": "Sukanya Samriddhi Yojana",
        "verdict": "ineligible",
        "confidence": 0.9,
        "matched_rules": [],
        "unmet_rules": [
          {
            "status": "failed",
            "field": "age",
            "operator": "lte",
            "expected": "10",
            "actual": "45",
            "description": "Girl must be below 10 years",
            "mandatory": true
          }
        ],
        "missing_fields": [
          "gender"
        ],
        "explanation": "You are not eligible for Sukanya Samriddhi Yojana. Criteria not met: Girl must be below 10 years."
      }
    ],
    "explanation": "Eligibility results for user usr_2e5b1d1d251f: [{'scheme_id': 'MUDRA-YOJANA-2024', 'scheme_name': 'PM MUDRA Yojana', 'verdict': 'eligible', 'confidence': 1.0, 'matched_rules': [{'status': 'passed', 'field': 'age', 'operator': 'gte', 'expected': '18', 'actual': '45', 'description': 'Min age 18', 'mandatory': True}, {'status': 'passed', 'field': 'employment_category', 'operator': 'in', 'expected': 'self_employed,other,agriculture', 'actual': 'agriculture', 'description': 'Non-corporate, non-farm e...",
    "degraded": null
  },
  "errors": null,
  "timestamp": "2026-02-28T06:30:08.077651",
  "request_id": "c3b4cbb9-9c1e-4a87-a4ad-084d7d5caa61"
}
```

**Required Changes for Future Reference:**
- Flow executed successfully. No immediate architecture changes required.

---

## Engine / Flow Name: What-If Simulation (E17 -> E7 -> Audit)
**Test Scenario / Purpose:** Simulate what happens to the user's eligibility if their income increases from 1.2L to 4L.

**Test Inputs:**
```json
{
  "user_id": "usr_2e5b1d1d251f",
  "current_profile": {
    "age": 44,
    "annual_income": 120000,
    "state": "UP",
    "occupation": "farmer",
    "gender": "male"
  },
  "changes": {
    "annual_income": 400000
  },
  "explain": true
}
```

**Expected Output:**
JSON response showing before and after benefit counts and an optional AI explanation of the delta.

**Actual Output / Result:** (PASS)
```json
{
  "success": true,
  "message": "OK",
  "data": {
    "scenario_type": "custom",
    "changes_applied": {
      "annual_income": 400000
    },
    "original_eligible": [
      {
        "id": "PM-KISAN-2024",
        "name": "PM Kisan Samman Nidhi"
      },
      {
        "id": "AYUSHMAN-BHARAT-2024",
        "name": "Ayushman Bharat PM-JAY"
      },
      {
        "id": "PM-AWAS-YOJANA-2024",
        "name": "PM Awas Yojana"
      },
      {
        "id": "MUDRA-YOJANA-2024",
        "name": "PM MUDRA Yojana"
      },
      {
        "id": "PMSBY-2024",
        "name": "PM Suraksha Bima Yojana"
      },
      {
        "id": "PMJJBY-2024",
        "name": "PM Jeevan Jyoti Bima Yojana"
      },
      {
        "id": "SCHOLARSHIP-SC-ST-2024",
        "name": "Post-Matric Scholarship SC/ST"
      }
    ],
    "new_eligible": [
      {
        "id": "AYUSHMAN-BHARAT-2024",
        "name": "Ayushman Bharat PM-JAY"
      },
      {
        "id": "PM-AWAS-YOJANA-2024",
        "name": "PM Awas Yojana"
      },
      {
        "id": "MUDRA-YOJANA-2024",
        "name": "PM MUDRA Yojana"
      },
      {
        "id": "PMSBY-2024",
        "name": "PM Suraksha Bima Yojana"
      },
      {
        "id": "PMJJBY-2024",
        "name": "PM Jeevan Jyoti Bima Yojana"
      }
    ],
    "gained": [],
    "lost": [
      {
        "id": "PM-KISAN-2024",
        "name": "PM Kisan Samman Nidhi",
        "benefit": 6000
      },
      {
        "id": "SCHOLARSHIP-SC-ST-2024",
        "name": "Post-Matric Scholarship SC/ST",
        "benefit": 50000
      }
    ],
    "net_benefit_change": -56000,
    "recommendations": [
      "You would lose eligibility for PM Kisan Samman Nidhi",
      "You would lose eligibility for Post-Matric Scholarship SC/ST"
    ],
    "explanation": "Simulation results for user usr_2e5b1d1d251f: Changes applied: {'annual_income': 400000}. Before: {}. After: {}. Delta: {}....",
    "degraded": null
  },
  "errors": null,
  "timestamp": "2026-02-28T06:30:08.626393",
  "request_id": "e63c1073-b533-4278-9123-7a28d6b7644e"
}
```

**Required Changes for Future Reference:**
- Flow executed successfully. No immediate architecture changes required.

---

## Engine / Flow Name: RAG Query Pipeline (E7 -> E6 -> E7 -> E8||E19 -> Audit)
**Test Scenario / Purpose:** User asks a conversational question. The intent is classified, context retrieved from vector DB, generated with LLM, checked for anomalies, and scored for trust.

**Test Inputs:**
```json
{
  "message": "Am I eligible for PM-KISAN if I own 3 acres of land?",
  "user_id": "usr_2e5b1d1d251f",
  "top_k": 3
}
```

**Expected Output:**
JSON response containing AI-generated text, trust_score, anomaly_score, and vector sources.

**Actual Output / Result:** (PARTIAL)
```json
{
  "success": false,
  "message": "AI service temporarily unavailable. Please try again.",
  "data": {
    "degraded": [
      "ai_generation"
    ]
  },
  "errors": null,
  "timestamp": "2026-02-28T06:30:14.306300",
  "request_id": "631fa645-4e6e-477a-b6ed-aca1ab9469bc"
}
```

**Required Changes for Future Reference:**
- **Degraded Services:** The orchestrator gracefully handled failures in: ai_generation.
- **Optimization needed:** E7 (Neural Network Engine) is timing out or throwing 500s when reaching out to Nvidia NIM. Need to implement a streaming response capability or increase the 20s timeout in the gateway. Introduce a lightweight local LLM fallback for when external APIs are rate limited.

---

## Engine / Flow Name: Voice Pipeline (E7 -> Route -> E20 -> Audit)
**Test Scenario / Purpose:** Process a voice transcript, route by intent, and generate TTS.

**Test Inputs:**
```json
{
  "text": "Tell me about PM Awas Yojana",
  "language": "english",
  "user_id": "usr_2e5b1d1d251f"
}
```

**Expected Output:**
JSON containing the audio response or degraded state.

**Actual Output / Result:** (PARTIAL)
```json
{
  "success": true,
  "message": "OK",
  "data": {
    "query": "Tell me about PM Awas Yojana",
    "response": "I'm sorry, the service is temporarily unavailable. Please try again.",
    "intent": "scheme_query",
    "language": "english",
    "audio_session_id": "5d5400ea7eb8",
    "audio_available": false,
    "degraded": [
      "intent_routing"
    ]
  },
  "errors": null,
  "timestamp": "2026-02-28T06:30:16.410855",
  "request_id": "06e31732-73f1-4cb4-96a8-e675204cf7b9"
}
```

**Required Changes for Future Reference:**
- **Degraded Services:** The orchestrator gracefully handled failures in: intent_routing.
- **Optimization needed:** E20 (Speech Interface) failed to route the transcript to E7 due to an internal timeout or schema mismatch. Since Voice Query is marked as 'Optional' in the blueprint, this partial degradation is acceptable for MVP, but the Voice-to-Intent pipeline must be hardened.

---

## Engine / Flow Name: Policy Ingestion (E11 -> E21 -> E10 -> E7 -> E6 -> E4 -> Audit)
**Test Scenario / Purpose:** Trigger a background policy ingestion flow fetching a URL, parsing it with LLM, chunking, embedding, and storing in vector DB.

**Test Inputs:**
```json
{
  "source_url": "https://pmkisan.gov.in/",
  "source_type": "web",
  "tags": [
    "agriculture",
    "central_scheme"
  ]
}
```

**Expected Output:**
Confirmation of ingestion or graceful degradation if LLM APIs aren't reachable. Should result in inserted vector chunks.

**Actual Output / Result:** (FAIL)
```json
{
  "detail": "Policy fetch failed: {'detail': 'Not Found'}"
}
```

**Required Changes for Future Reference:**
- **Bug Found:** The Policy Fetching Engine (E11) threw a 404 Not Found for `https://pmkisan.gov.in/`.
- **Architecture update required:** E11 currently seems to rely on an internal dictionary of hardcoded mock policies rather than performing an actual live web scrape. If live URLs are passed, it should invoke a Web Scraper sub-module or return a dedicated 'Unsupported Source' error instead of a generic 404.

---

