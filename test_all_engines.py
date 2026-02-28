"""
AIforBharat — Comprehensive Engine Test Script
================================================
Tests all 21 engines: starts each on its port, runs health + key endpoint tests,
then stops it before moving to the next.
"""

import subprocess
import time
import sys
import json
import httpx
import os

os.chdir(r"d:\AIForBharat\AIforBharat")

RESULTS = []

def start_engine(module, port, wait=6.0):
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", f"{module}.main:app", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=r"d:\AIForBharat\AIforBharat",
    )
    # Poll health endpoint instead of just sleeping — some engines need
    # extra time for DB seeding (E11, E15, E16, E18)
    deadline = time.time() + max(wait, 15.0)
    while time.time() < deadline:
        time.sleep(1)
        try:
            r = httpx.get(f"http://localhost:{port}/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
    return proc

def stop_engine(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except:
        proc.kill()
    # Give OS time to release file handles and ports (Windows specific)
    time.sleep(2)

def test_get(url, label):
    try:
        r = httpx.get(url, timeout=10)
        return {"endpoint": label, "method": "GET", "url": url, "status": r.status_code, "response": r.json() if r.status_code < 500 else r.text[:200]}
    except Exception as e:
        return {"endpoint": label, "method": "GET", "url": url, "status": "ERROR", "response": str(e)[:200]}

def test_post(url, label, payload):
    try:
        r = httpx.post(url, json=payload, timeout=15)
        try:
            body = r.json()
        except:
            body = r.text[:200]
        return {"endpoint": label, "method": "POST", "url": url, "status": r.status_code, "response": body}
    except Exception as e:
        return {"endpoint": label, "method": "POST", "url": url, "status": "ERROR", "response": str(e)[:200]}

def test_engine(name, module, port, tests):
    print(f"\n{'='*60}")
    print(f"  TESTING: {name} (port {port})")
    print(f"{'='*60}")
    
    proc = start_engine(module, port)
    engine_results = {"engine": name, "port": port, "module": module, "tests": []}
    
    for t in tests:
        if t["method"] == "GET":
            result = test_get(f"http://localhost:{port}{t['path']}", t["label"])
        else:
            result = test_post(f"http://localhost:{port}{t['path']}", t["label"], t.get("payload", {}))
        
        status_icon = "PASS" if isinstance(result["status"], int) and result["status"] < 400 else "FAIL" if isinstance(result["status"], int) and result["status"] >= 400 else "ERR"
        print(f"  [{status_icon}] {t['label']}: {result['status']}")
        engine_results["tests"].append(result)
    
    stop_engine(proc)
    RESULTS.append(engine_results)
    return engine_results

ENGINES = [
    {
        "name": "Engine 1 - Login & Register",
        "module": "login-register-engine",
        "port": 8001,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "POST", "path": "/auth/register", "label": "Register User", "payload": {
                "phone": "9876543210", "password": "Test@12345", "name": "Test User", "consent_data_processing": True
            }},
            {"method": "POST", "path": "/auth/login", "label": "Login", "payload": {
                "phone": "9876543210", "password": "Test@12345"
            }},
        ]
    },
    {
        "name": "Engine 2 - Identity Engine",
        "module": "identity-engine",
        "port": 8002,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "POST", "path": "/identity/create", "label": "Create Identity", "payload": {
                "user_id": "usr_test001", "full_name": "Test User", "aadhaar_number": "123456789012",
                "pan_number": "ABCDE1234F", "address": "123 Main St, Delhi",
                "date_of_birth": "1990-01-15", "gender": "male", "caste_category": "General",
                "state": "Delhi", "district": "New Delhi", "phone": "9876543210"
            }},
        ]
    },
    {
        "name": "Engine 3 - Raw Data Store",
        "module": "raw-data-store",
        "port": 8003,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "POST", "path": "/raw-data/events", "label": "Store Event", "payload": {
                "event_type": "TEST_EVENT", "source_engine": "test_script", "user_id": "usr_test001",
                "payload": {"action": "testing", "engine": "raw_data_store"}
            }},
            {"method": "GET", "path": "/raw-data/events", "label": "List Events"},
        ]
    },
    {
        "name": "Engine 4 - Metadata Engine",
        "module": "metadata-engine",
        "port": 8004,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "POST", "path": "/metadata/process", "label": "Process Metadata", "payload": {
                "user_id": "usr_test001", "age": 35, "gender": "male", "state": "Bihar",
                "district": "Patna", "annual_income": 180000, "occupation": "farmer",
                "caste_category": "OBC", "land_holding_acres": 3.5, "education": "secondary",
                "marital_status": "married", "dependents": 3
            }},
        ]
    },
    {
        "name": "Engine 5 - Processed Metadata Store",
        "module": "processed-user-metadata-store",
        "port": 8005,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "POST", "path": "/processed-metadata/store", "label": "Store Metadata", "payload": {
                "user_id": "usr_test001",
                "processed_data": {
                    "full_name": "Test User", "phone": "9876543210",
                    "age": 35, "gender": "male", "state": "Bihar", "district": "Patna",
                    "annual_income": 180000, "occupation": "farmer", "caste_category": "OBC",
                    "education": "secondary", "marital_status": "married"
                }
            }},
        ]
    },
    {
        "name": "Engine 6 - Vector Database",
        "module": "vector-database",
        "port": 8006,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "GET", "path": "/vectors/stats", "label": "Vector Stats"},
            {"method": "POST", "path": "/vectors/upsert", "label": "Upsert Vector", "payload": {
                "id": "test_vec_001", "content": "PM-KISAN provides income support to farmer families",
                "document_id": "policy_pmkisan", "metadata": {"scheme": "PM-KISAN"}
            }},
        ]
    },
    {
        "name": "Engine 7 - Neural Network",
        "module": "neural-network-engine",
        "port": 8007,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "POST", "path": "/ai/intent", "label": "Intent Classification", "payload": {
                "message": "Tell me about PM-KISAN scheme"
            }},
        ]
    },
    {
        "name": "Engine 8 - Anomaly Detection",
        "module": "anomaly-detection-engine",
        "port": 8008,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "POST", "path": "/anomaly/check", "label": "Anomaly Check", "payload": {
                "user_id": "usr_test001",
                "profile": {"name": "Test User", "phone": "9876543210", "age": 35,
                    "annual_income": 180000, "occupation": "farmer", "state": "Bihar"}
            }},
            {"method": "GET", "path": "/anomaly/stats", "label": "Anomaly Stats"},
        ]
    },
    {
        "name": "Engine 9 - API Gateway",
        "module": "api-gateway",
        "port": 8000,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "GET", "path": "/", "label": "Service Directory"},
        ]
    },
    {
        "name": "Engine 10 - Chunks Engine",
        "module": "chunks-engine",
        "port": 8010,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "GET", "path": "/chunks/stats", "label": "Chunk Stats"},
            {"method": "POST", "path": "/chunks/create", "label": "Create Chunks", "payload": {
                "document_id": "doc_test001",
                "text": "PM-KISAN is a Central Sector scheme providing income support of Rs.6000 per year to farmer families. The scheme aims to supplement the financial needs of the farmers in procuring various inputs to ensure proper crop health.",
                "strategy": "fixed", "chunk_size": 100, "overlap": 20
            }},
        ]
    },
    {
        "name": "Engine 11 - Policy Fetching",
        "module": "policy-fetching-engine",
        "port": 8011,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "GET", "path": "/policies/list", "label": "List Policies"},
            {"method": "GET", "path": "/policies/sources/list", "label": "List Sources"},
        ]
    },
    {
        "name": "Engine 12 - JSON User Info Generator",
        "module": "json-user-info-generator",
        "port": 8012,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "POST", "path": "/profile/generate", "label": "Generate Profile", "payload": {
                "user_id": "usr_test001"
            }},
        ]
    },
    {
        "name": "Engine 13 - Analytics Warehouse",
        "module": "analytics-warehouse",
        "port": 8013,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "GET", "path": "/analytics/dashboard", "label": "Dashboard Summary"},
            {"method": "POST", "path": "/analytics/events", "label": "Record Event", "payload": {
                "event_type": "test_event", "user_id": "usr_test001", "engine": "test_script",
                "payload": {"action": "testing"}
            }},
        ]
    },
    {
        "name": "Engine 14 - Dashboard Interface",
        "module": "dashboard-interface",
        "port": 8014,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "GET", "path": "/dashboard/engines/status", "label": "Engines Status"},
            {"method": "GET", "path": "/dashboard/schemes", "label": "Schemes Listing"},
            {"method": "GET", "path": "/dashboard/search?q=kisan", "label": "Search"},
        ]
    },
    {
        "name": "Engine 15 - Eligibility Rules",
        "module": "eligibility-rules-engine",
        "port": 8015,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "GET", "path": "/eligibility/schemes", "label": "List Schemes"},
            {"method": "POST", "path": "/eligibility/check", "label": "Check Eligibility", "payload": {
                "user_id": "usr_test001",
                "profile": {
                    "age": 35, "annual_income": 180000, "state": "Bihar",
                    "occupation": "farmer", "land_holding_acres": 3.5,
                    "caste_category": "OBC", "gender": "male"
                }
            }},
        ]
    },
    {
        "name": "Engine 16 - Deadline Monitoring",
        "module": "deadline-monitoring-engine",
        "port": 8016,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "GET", "path": "/deadlines/list", "label": "List Deadlines"},
            {"method": "POST", "path": "/deadlines/check", "label": "Check Deadlines", "payload": {
                "user_id": "usr_test001"
            }},
        ]
    },
    {
        "name": "Engine 17 - Simulation Engine",
        "module": "simulation-engine",
        "port": 8017,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "POST", "path": "/simulate/what-if", "label": "What-If Simulation", "payload": {
                "user_id": "usr_test001",
                "current_profile": {"age": 28, "annual_income": 400000, "occupation": "salaried", "gender": "male", "state": "Delhi"},
                "changes": {"annual_income": 180000, "occupation": "farmer", "state": "Bihar", "land_holding_acres": 3}
            }},
            {"method": "POST", "path": "/simulate/life-event", "label": "Life Event Simulation", "payload": {
                "user_id": "usr_test001",
                "current_profile": {"age": 28, "annual_income": 400000, "occupation": "salaried", "gender": "male", "state": "Delhi"},
                "life_event": "job_loss"
            }},
        ]
    },
    {
        "name": "Engine 18 - Gov Data Sync",
        "module": "government-data-sync-engine",
        "port": 8018,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "GET", "path": "/gov-data/datasets", "label": "List Datasets"},
        ]
    },
    {
        "name": "Engine 19 - Trust Scoring",
        "module": "trust-scoring-engine",
        "port": 8019,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "POST", "path": "/trust/compute", "label": "Compute Trust Score", "payload": {
                "user_id": "usr_test001",
                "profile": {"name": "Test User", "phone": "9876543210", "age": 35,
                    "annual_income": 180000, "occupation": "farmer", "state": "Bihar",
                    "gender": "male", "district": "Patna", "caste_category": "OBC"}
            }},
        ]
    },
    {
        "name": "Engine 20 - Speech Interface",
        "module": "speech-interface-engine",
        "port": 8020,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "GET", "path": "/speech/languages", "label": "List Languages"},
            {"method": "POST", "path": "/speech/detect-language", "label": "Detect Language", "payload": {
                "text": "Tell me about government schemes"
            }},
        ]
    },
    {
        "name": "Engine 21 - Document Understanding",
        "module": "document-understanding-engine",
        "port": 8021,
        "tests": [
            {"method": "GET", "path": "/health", "label": "Health Check"},
            {"method": "POST", "path": "/documents/parse", "label": "Parse Document", "payload": {
                "policy_id": "pol_test001",
                "text": "PM-KISAN: Eligibility criteria include being a farmer with land holding up to 5 acres and annual income below Rs. 6,00,000. Benefits include Rs. 6000 per year. Deadline for application is March 31, 2025.",
                "title": "PM-KISAN Overview"
            }},
        ]
    },
]

if __name__ == "__main__":
    print("=" * 60)
    print("  AIforBharat - Testing All 21 Engines")
    print("=" * 60)
    
    for engine in ENGINES:
        try:
            test_engine(engine["name"], engine["module"], engine["port"], engine["tests"])
        except Exception as e:
            print(f"  [ERR] {engine['name']} FAILED TO START: {e}")
            RESULTS.append({"engine": engine["name"], "port": engine["port"], "tests": [{"endpoint": "STARTUP", "status": "CRASH", "response": str(e)[:200]}]})
        time.sleep(2)

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    total_tests = 0
    passed = 0
    failed = 0
    errors = 0
    
    for r in RESULTS:
        for t in r["tests"]:
            total_tests += 1
            if isinstance(t["status"], int) and t["status"] < 400:
                passed += 1
            elif isinstance(t["status"], int) and t["status"] >= 400:
                failed += 1
            else:
                errors += 1
    
    print(f"\n  Total Tests:  {total_tests}")
    print(f"  Passed:       {passed}")
    print(f"  Failed:       {failed}")
    print(f"  Errors:       {errors}")
    
    print("\n  Per-Engine Results:")
    for r in RESULTS:
        engine_pass = sum(1 for t in r["tests"] if isinstance(t["status"], int) and t["status"] < 400)
        engine_total = len(r["tests"])
        icon = "PASS" if engine_pass == engine_total else "WARN" if engine_pass > 0 else "FAIL"
        print(f"  [{icon}] {r['engine']} (:{r['port']}): {engine_pass}/{engine_total} passed")
    
    os.makedirs(r"d:\AIForBharat\AIforBharat\data", exist_ok=True)
    with open(r"d:\AIForBharat\AIforBharat\data\test_results.json", "w") as f:
        json.dump(RESULTS, f, indent=2, default=str)
    print(f"\n  Detailed results saved to data/test_results.json")
