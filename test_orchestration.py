import os
import sys
import time
import httpx
import json
import subprocess
import random

os.chdir(r"d:\AIForBharat\AIforBharat")

ENGINES = [
    {"name": "Engine 1 - Login & Register", "module": "login-register-engine", "port": 8001},
    {"name": "Engine 2 - Identity Engine", "module": "identity-engine", "port": 8002},
    {"name": "Engine 3 - Raw Data Store", "module": "raw-data-store", "port": 8003},
    {"name": "Engine 4 - Metadata Engine", "module": "metadata-engine", "port": 8004},
    {"name": "Engine 5 - Processed Metadata", "module": "processed-user-metadata-store", "port": 8005},
    {"name": "Engine 6 - Vector Database", "module": "vector-database", "port": 8006},
    {"name": "Engine 7 - Neural Network", "module": "neural-network-engine", "port": 8007},
    {"name": "Engine 8 - Anomaly Detection", "module": "anomaly-detection-engine", "port": 8008},
    {"name": "Engine 9 - API Gateway", "module": "api-gateway", "port": 8000}, # start it a bit later, or together
    {"name": "Engine 10 - Chunks Engine", "module": "chunks-engine", "port": 8010},
    {"name": "Engine 11 - Policy Fetching", "module": "policy-fetching-engine", "port": 8011},
    {"name": "Engine 12 - JSON User Info Gen", "module": "json-user-info-generator", "port": 8012},
    {"name": "Engine 13 - Analytics Warehouse", "module": "analytics-warehouse", "port": 8013},
    {"name": "Engine 14 - Dashboard", "module": "dashboard-interface", "port": 8014},
    {"name": "Engine 15 - Eligibility Rules", "module": "eligibility-rules-engine", "port": 8015},
    {"name": "Engine 16 - Deadline Monitoring", "module": "deadline-monitoring-engine", "port": 8016},
    {"name": "Engine 17 - Simulation Engine", "module": "simulation-engine", "port": 8017},
    {"name": "Engine 18 - Gov Data Sync", "module": "government-data-sync-engine", "port": 8018},
    {"name": "Engine 19 - Trust Scoring", "module": "trust-scoring-engine", "port": 8019},
    {"name": "Engine 20 - Speech Interface", "module": "speech-interface-engine", "port": 8020},
    {"name": "Engine 21 - Doc Understanding", "module": "document-understanding-engine", "port": 8021},
]

procs = []

def start_engines():
    print("Starting all 21 engines concurrently...")
    for eng in ENGINES:
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", f"{eng['module']}.main:app", "--port", str(eng["port"])],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=r"d:\AIForBharat\AIforBharat"
        )
        procs.append(p)
    print("Waiting for absolute startup time (15s)...")
    time.sleep(15)

def stop_engines():
    print("Stopping all engines...")
    for p in procs:
        p.terminate()
        try:
            p.wait(timeout=3)
        except:
            p.kill()

def wait_for_health():
    unhealthy = []
    with httpx.Client(timeout=5) as client:
        for eng in ENGINES:
            url = f"http://127.0.0.1:{eng['port']}/health"
            try:
                r = client.get(url)
                if r.status_code != 200:
                    unhealthy.append(eng["name"])
            except:
                unhealthy.append(eng["name"])
    if unhealthy:
        print("WARNING: The following engines are NOT healthy or failed to start:", unhealthy)
    else:
        print("All engines are healthy!")
    return unhealthy

def generate_markdown(tests):
    md = "# AIforBharat Orchestration Testing Report\n\n"
    md += "> **Execution Context**: Local execution, 21 engines running concurrently behind API Gateway (E0:8000)\n\n"
    
    for t in tests:
        md += f"## Engine / Flow Name: {t['flow_name']}\n"
        md += f"**Test Scenario / Purpose:** {t['scenario']}\n\n"
        md += f"**Test Inputs:**\n```json\n{json.dumps(t['inputs'], indent=2)}\n```\n\n"
        md += f"**Expected Output:**\n{t['expected']}\n\n"
        
        # Determine status
        if t['actual_status'] >= 500:
            status_mark = "FAIL"
        elif "degraded" in t['actual_response_str'] and t['actual_response'].get("data", {}).get("degraded"):
            status_mark = "PARTIAL"
        elif t['actual_status'] >= 400:
            status_mark = "FAIL"  # Validation or routing error
        else:
            status_mark = "PASS"
            
        md += f"**Actual Output / Result:** ({status_mark})\n"
        md += f"```json\n{json.dumps(t['actual_response'], indent=2)}\n```\n\n"
        
        md += f"**Required Changes for Future Reference:**\n"
        
        # Automatically generate some suggested changes based on degraded arrays or errors
        if status_mark == "PASS":
            md += "- Flow executed successfully. No immediate architecture changes required.\n"
        else:
            if "degraded" in t['actual_response_str']:
                degraded_list = []
                try:
                     degraded_list = t['actual_response'].get("data", {}).get("degraded", [])
                except: pass
                md += f"- **Degraded Services:** The orchestrator gracefully handled failures in: {', '.join(degraded_list)}.\n"
                md += "- **Optimization needed:** Investigate the failing downstream services to understand why they timed out or threw 500s.\n"
            if t['actual_status'] == 422:
                md += "- **Bug Found:** The request payload was rejected by Pydantic validation. The Orchestrator's expected schema and the test payload are mismatched.\n"
            elif t['actual_status'] >= 500:
                md += "- **Bug Found:** The API Gateway or Orchestrator threw an internal server error. Circuit breaker may not have caught this properly, or a critical engine failed.\n"
            
            # Additional context checks
            if "Connection Refused" in t['actual_response_str']:
                md += "- **Architecture update required:** Ensure dependent engines (like Vector DB or LLM mock) are actually starting correctly or add a mock-fallback mode if external APIs (like NVIDIA NIM) are unreachable.\n"
                
        md += "\n---\n\n"
    
    with open("orchestra-testing-1.md", "w", encoding="utf-8") as f:
        f.write(md)


def run_orchestration_tests():
    base_url = "http://127.0.0.1:8000/api/v1"
    client = httpx.Client(timeout=45.0)  # Generous timeout for chained calls
    
    tests = []
    
    # 1. Onboarding
    test_phone = f"98{random.randint(10000000, 99999999)}"
    payload_onboard = {
        "phone": test_phone,
        "password": "SecurePassword123!",
        "name": "Raj Kumar",
        "state": "UP",
        "district": "Lucknow",
        "language_preference": "hi",
        "consent_data_processing": True,
        "date_of_birth": "1980-05-15",
        "annual_income": 120000.0,
        "occupation": "farmer"
    }
    print("Testing Onboarding...")
    r1 = client.post(f"{base_url}/onboard", json=payload_onboard)
    tests.append({
        "flow_name": "User Onboarding Flow (E1 -> E2 -> E4 -> E5 -> E15||E16 -> E12 -> Audit)",
        "scenario": "A new user registers and their profile is created, metadata is normalized, eligibility is batch-checked, and deadlines are listed.",
        "inputs": payload_onboard,
        "expected": "A JSON response containing the user_id, access_token, identity_token, eligibility_summary, and upcoming_deadlines. It should gracefully degrade if any non-critical engine fails.",
        "actual_status": r1.status_code,
        "actual_response": r1.json() if r1.text else {},
        "actual_response_str": r1.text
    })

    # Get user details for next steps
    user_id_created = "usr_fallback_999"
    access_token = ""
    try:
        user_id_created = r1.json().get("data", {}).get("user_id", "usr_fallback_999")
        access_token = r1.json().get("data", {}).get("access_token", "")
    except: pass
    
    auth_headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    
    # 2. Eligibility
    payload_eligibility = {
        "user_id": user_id_created,
        "profile": {
             "age": 44, "annual_income": 120000, "state": "UP", "occupation": "farmer", "gender": "male"
        },
        "explain": True
    }
    print("Testing Eligibility Check...")
    r2 = client.post(f"{base_url}/check-eligibility", json=payload_eligibility, headers=auth_headers)
    tests.append({
        "flow_name": "Eligibility Check with Explanation (E15 -> E7 -> Audit)",
        "scenario": "Evaluate eligibility based on user profile and generate a human-readable explanation using the LLM.",
        "inputs": payload_eligibility,
        "expected": "A JSON response with deterministic rules evaluation from E15, and an AI-generated explanation from E7.",
        "actual_status": r2.status_code,
        "actual_response": r2.json() if r2.text else {},
        "actual_response_str": r2.text
    })

    # 3. Simulation
    payload_simulate = {
        "user_id": user_id_created,
        "current_profile": {
             "age": 44, "annual_income": 120000, "state": "UP", "occupation": "farmer", "gender": "male"
        },
        "changes": {
            "annual_income": 400000
        },
        "explain": True
    }
    print("Testing What-If Simulation...")
    r3 = client.post(f"{base_url}/simulate", json=payload_simulate, headers=auth_headers)
    tests.append({
        "flow_name": "What-If Simulation (E17 -> E7 -> Audit)",
        "scenario": "Simulate what happens to the user's eligibility if their income increases from 1.2L to 4L.",
        "inputs": payload_simulate,
        "expected": "JSON response showing before and after benefit counts and an optional AI explanation of the delta.",
        "actual_status": r3.status_code,
        "actual_response": r3.json() if r3.text else {},
        "actual_response_str": r3.text
    })

    # 4. RAG Query
    payload_query = {
        "message": "Am I eligible for PM-KISAN if I own 3 acres of land?",
        "user_id": user_id_created,
        "top_k": 3
    }
    print("Testing RAG Query...")
    r4 = client.post(f"{base_url}/query", json=payload_query, headers=auth_headers)
    tests.append({
        "flow_name": "RAG Query Pipeline (E7 -> E6 -> E7 -> E8||E19 -> Audit)",
        "scenario": "User asks a conversational question. The intent is classified, context retrieved from vector DB, generated with LLM, checked for anomalies, and scored for trust.",
        "inputs": payload_query,
        "expected": "JSON response containing AI-generated text, trust_score, anomaly_score, and vector sources.",
        "actual_status": r4.status_code,
        "actual_response": r4.json() if r4.text else {},
        "actual_response_str": r4.text
    })

    # 5. Voice Query
    payload_voice = {
        "text": "Tell me about PM Awas Yojana",
        "language": "english",
        "user_id": user_id_created
    }
    print("Testing Voice Query...")
    r5 = client.post(f"{base_url}/voice-query", json=payload_voice, headers=auth_headers)
    tests.append({
        "flow_name": "Voice Pipeline (E7 -> Route -> E20 -> Audit)",
        "scenario": "Process a voice transcript, route by intent, and generate TTS.",
        "inputs": payload_voice,
        "expected": "JSON containing the audio response or degraded state.",
        "actual_status": r5.status_code,
        "actual_response": r5.json() if r5.text else {},
        "actual_response_str": r5.text
    })

    # 6. Policy Ingestion
    payload_policy = {
        "source_url": "https://pmkisan.gov.in/",
        "source_type": "web",
        "tags": ["agriculture", "central_scheme"]
    }
    print("Testing Policy Ingestion...")
    r6 = client.post(f"{base_url}/ingest-policy", json=payload_policy, headers=auth_headers)
    tests.append({
        "flow_name": "Policy Ingestion (E11 -> E21 -> E10 -> E7 -> E6 -> E4 -> Audit)",
        "scenario": "Trigger a background policy ingestion flow fetching a URL, parsing it with LLM, chunking, embedding, and storing in vector DB.",
        "inputs": payload_policy,
        "expected": "Confirmation of ingestion or graceful degradation if LLM APIs aren't reachable. Should result in inserted vector chunks.",
        "actual_status": r6.status_code,
        "actual_response": r6.json() if r6.text else {},
        "actual_response_str": r6.text
    })

    generate_markdown(tests)
    print("Tests completed. Output saved to orchestra-testing-1.md")


if __name__ == "__main__":
    try:
        start_engines()
        wait_for_health()
        run_orchestration_tests()
    finally:
        stop_engines()
