import httpx
import asyncio
import json

ENGINES = {
    "api-gateway": 8000,
    "login-register-engine": 8001,
    "identity-engine": 8002,
    "raw-data-store": 8003,
    "metadata-engine": 8004,
    "processed-user-metadata-store": 8005,
    "vector-database": 8006,
    "neural-network-engine": 8007,
    "anomaly-detection-engine": 8008,
    "chunks-engine": 8010,
    "policy-fetching-engine": 8011,
    "json-user-info-generator": 8012,
    "analytics-warehouse": 8013,
    "dashboard-interface": 8014,
    "eligibility-rules-engine": 8015,
    "deadline-monitoring-engine": 8016,
    "simulation-engine": 8017,
    "government-data-sync-engine": 8018,
    "trust-scoring-engine": 8019,
    "speech-interface-engine": 8020,
    "document-understanding-engine": 8021
}

async def check_engine_health():
    results = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, port in ENGINES.items():
            try:
                response = await client.get(f"http://localhost:{port}/health")
                results[name] = {"status": response.status_code, "ok": response.status_code == 200, "error": None}
            except Exception as e:
                try:
                    response = await client.get(f"http://localhost:{port}/api/v1/engines/health")
                    results[name] = {"status": response.status_code, "ok": response.status_code == 200, "error": None}
                except Exception as e2:
                    results[name] = {"status": None, "ok": False, "error": str(e2)}
    return results

async def main():
    print("Testing Engine Health...")
    health_results = await check_engine_health()
    print(json.dumps(health_results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
