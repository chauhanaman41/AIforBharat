"""
API Gateway — Route Definitions
=================================
Proxies requests to the appropriate downstream engine.
Each engine runs on its own port locally.
In production, these would be Kubernetes service DNS names.
"""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse

from shared.config import settings, ENGINE_URLS
from shared.models import ApiResponse
from shared.utils import decode_token

logger = logging.getLogger("api_gateway.routes")

gateway_router = APIRouter()


# ── JWT Authentication Dependency ─────────────────────────────────────────────

async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Extract and validate JWT from Authorization header.
    Returns decoded payload or None for public endpoints.
    """
    if not authorization:
        return None

    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            return None
        payload = decode_token(token)
        return payload
    except Exception:
        return None


async def require_auth(authorization: Optional[str] = Header(None)) -> dict:
    """Mandatory auth for protected endpoints. Raises 401 if invalid."""
    user = await get_current_user(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


# ── Proxy Helper ──────────────────────────────────────────────────────────────

async def proxy_request(
    engine_url: str,
    path: str,
    request: Request,
    method: str = None,
) -> JSONResponse:
    """
    Forward a request to a downstream engine.
    Preserves headers, body, query parameters.
    Implements circuit breaker pattern (timeout-based).
    """
    method = method or request.method
    target_url = f"{engine_url}{path}"

    # Forward relevant headers
    headers = {
        "Content-Type": request.headers.get("content-type", "application/json"),
        "X-Request-ID": getattr(request.state, "request_id", ""),
    }
    if "authorization" in request.headers:
        headers["Authorization"] = request.headers["authorization"]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            body = await request.body()
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body if body else None,
                params=dict(request.query_params),
            )
            return JSONResponse(
                status_code=response.status_code,
                content=response.json() if response.content else None,
            )
    except httpx.ConnectError:
        logger.error(f"Engine unavailable: {engine_url}")
        raise HTTPException(
            status_code=503,
            detail=f"Service temporarily unavailable. The engine at {engine_url} is not responding.",
        )
    except httpx.TimeoutException:
        logger.error(f"Engine timeout: {engine_url}")
        raise HTTPException(status_code=504, detail="Gateway timeout — engine did not respond in time.")
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        raise HTTPException(status_code=502, detail=f"Bad gateway: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# ROUTE GROUPS — Each maps to a downstream engine
# ══════════════════════════════════════════════════════════════════════════════


# ── Auth Routes (Engine 1: Login/Register) ────────────────────────────────────
@gateway_router.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["Auth"])
async def auth_proxy(path: str, request: Request):
    """Proxy auth requests to Login/Register Engine (port 8001)."""
    return await proxy_request(ENGINE_URLS["login_register"], f"/auth/{path}", request)


# ── Identity Routes (Engine 2) ────────────────────────────────────────────────
@gateway_router.api_route("/identity/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["Identity"])
async def identity_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy identity requests to Identity Engine (port 8002). Requires auth."""
    return await proxy_request(ENGINE_URLS["identity"], f"/identity/{path}", request)


# ── Metadata Routes (Engine 4) ────────────────────────────────────────────────
@gateway_router.api_route("/metadata/{path:path}", methods=["GET", "POST", "PUT"], tags=["Metadata"])
async def metadata_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy metadata requests to Metadata Engine (port 8004)."""
    return await proxy_request(ENGINE_URLS["metadata"], f"/metadata/{path}", request)


# ── Eligibility Routes (Engine 15) ────────────────────────────────────────────
@gateway_router.api_route("/eligibility/{path:path}", methods=["GET", "POST"], tags=["Eligibility"])
async def eligibility_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy eligibility requests to Eligibility Rules Engine (port 8015)."""
    return await proxy_request(ENGINE_URLS["eligibility_rules"], f"/eligibility/{path}", request)


# ── Schemes / Policies Routes (Engine 11 + 15) ───────────────────────────────
@gateway_router.api_route("/schemes/{path:path}", methods=["GET", "POST"], tags=["Schemes"])
async def schemes_proxy(path: str, request: Request):
    """Proxy scheme search/lookup to Policy Fetching Engine (port 8011)."""
    return await proxy_request(ENGINE_URLS["policy_fetching"], f"/schemes/{path}", request)


@gateway_router.api_route("/policies/{path:path}", methods=["GET", "POST"], tags=["Policies"])
async def policies_proxy(path: str, request: Request):
    """Proxy policy version/history requests to Policy Fetching Engine."""
    return await proxy_request(ENGINE_URLS["policy_fetching"], f"/policies/{path}", request)


# ── Simulation Routes (Engine 17) ─────────────────────────────────────────────
@gateway_router.api_route("/simulate/{path:path}", methods=["GET", "POST"], tags=["Simulation"])
async def simulation_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy simulation requests to Simulation Engine (port 8017)."""
    return await proxy_request(ENGINE_URLS["simulation"], f"/simulate/{path}", request)


# ── Deadline Routes (Engine 16) ───────────────────────────────────────────────
@gateway_router.api_route("/deadlines/{path:path}", methods=["GET", "POST", "PUT"], tags=["Deadlines"])
async def deadlines_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy deadline requests to Deadline Monitoring Engine (port 8016)."""
    return await proxy_request(ENGINE_URLS["deadline_monitoring"], f"/deadlines/{path}", request)


# ── AI / Neural Network Routes (Engine 7) ─────────────────────────────────────
@gateway_router.api_route("/ai/{path:path}", methods=["GET", "POST"], tags=["AI"])
async def ai_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy AI requests to Neural Network Engine (port 8007)."""
    return await proxy_request(ENGINE_URLS["neural_network"], f"/ai/{path}", request)


# ── Dashboard BFF Routes (Engine 14) ──────────────────────────────────────────
@gateway_router.api_route("/dashboard/{path:path}", methods=["GET", "POST", "PUT"], tags=["Dashboard"])
async def dashboard_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy dashboard requests to Dashboard BFF (port 8014)."""
    return await proxy_request(ENGINE_URLS["dashboard_bff"], f"/dashboard/{path}", request)


# ── Document Routes (Engine 21) ───────────────────────────────────────────────
@gateway_router.api_route("/documents/{path:path}", methods=["GET", "POST"], tags=["Documents"])
async def documents_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy document requests to Document Understanding Engine (port 8021)."""
    return await proxy_request(ENGINE_URLS["doc_understanding"], f"/documents/{path}", request)


# ── Voice / Speech Routes (Engine 20) ─────────────────────────────────────────
@gateway_router.api_route("/voice/{path:path}", methods=["GET", "POST", "PUT"], tags=["Voice"])
async def voice_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy voice requests to Speech Interface Engine (port 8020)."""
    return await proxy_request(ENGINE_URLS["speech_interface"], f"/voice/{path}", request)


# ── Analytics Routes (Engine 13) ──────────────────────────────────────────────
@gateway_router.api_route("/analytics/{path:path}", methods=["GET", "POST"], tags=["Analytics"])
async def analytics_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy analytics requests to Analytics Warehouse (port 8013)."""
    return await proxy_request(ENGINE_URLS["analytics_warehouse"], f"/analytics/{path}", request)


# ── Trust Scoring Routes (Engine 19) ──────────────────────────────────────────
@gateway_router.api_route("/trust/{path:path}", methods=["GET", "POST"], tags=["Trust"])
async def trust_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy trust requests to Trust Scoring Engine (port 8019)."""
    return await proxy_request(ENGINE_URLS["trust_scoring"], f"/trust/{path}", request)


# ── Profile / JSON User Info Routes (Engine 12) ──────────────────────────────
@gateway_router.api_route("/profile/{path:path}", methods=["GET", "POST"], tags=["Profile"])
async def profile_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy profile requests to JSON User Info Generator (port 8012)."""
    return await proxy_request(ENGINE_URLS["json_user_info"], f"/profile/{path}", request)


# ── Raw Data Store Routes (Engine 3) ──────────────────────────────────────────
@gateway_router.api_route("/raw-data/{path:path}", methods=["GET", "POST"], tags=["Raw Data"])
async def raw_data_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy raw data requests to Raw Data Store (port 8003)."""
    return await proxy_request(ENGINE_URLS["raw_data_store"], f"/raw-data/{path}", request)


# ── Processed Metadata Routes (Engine 5) ──────────────────────────────────────
@gateway_router.api_route("/processed-metadata/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["Processed Metadata"])
async def processed_metadata_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy processed metadata requests to Processed Metadata Store (port 8005)."""
    return await proxy_request(ENGINE_URLS["processed_metadata"], f"/processed-metadata/{path}", request)


# ── Vector Database Routes (Engine 6) ─────────────────────────────────────────
@gateway_router.api_route("/vectors/{path:path}", methods=["GET", "POST", "DELETE"], tags=["Vectors"])
async def vectors_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy vector requests to Vector Database (port 8006)."""
    return await proxy_request(ENGINE_URLS["vector_database"], f"/vectors/{path}", request)


# ── Anomaly Detection Routes (Engine 8) ───────────────────────────────────────
@gateway_router.api_route("/anomaly/{path:path}", methods=["GET", "POST", "PUT"], tags=["Anomaly"])
async def anomaly_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy anomaly requests to Anomaly Detection Engine (port 8008)."""
    return await proxy_request(ENGINE_URLS["anomaly_detection"], f"/anomaly/{path}", request)


# ── Chunks Engine Routes (Engine 10) ──────────────────────────────────────────
@gateway_router.api_route("/chunks/{path:path}", methods=["GET", "POST"], tags=["Chunks"])
async def chunks_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy chunk requests to Chunks Engine (port 8010)."""
    return await proxy_request(ENGINE_URLS["chunks"], f"/chunks/{path}", request)


# ── Gov Data Sync Routes (Engine 18) ─────────────────────────────────────────
@gateway_router.api_route("/gov-data/{path:path}", methods=["GET", "POST"], tags=["Gov Data"])
async def gov_data_proxy(path: str, request: Request, user=Depends(require_auth)):
    """Proxy gov data requests to Gov Data Sync Engine (port 8018)."""
    return await proxy_request(ENGINE_URLS["gov_data_sync"], f"/gov-data/{path}", request)


# ── Event Bus Debug (development only) ────────────────────────────────────────
@gateway_router.get("/debug/events", tags=["Debug"])
async def debug_events(user=Depends(require_auth)):
    """[DEV ONLY] View recent event bus messages."""
    from shared.event_bus import event_bus
    history = event_bus.get_history(limit=20)
    return ApiResponse(
        data={
            "recent_events": [e.model_dump(mode="json") for e in history],
            "stats": event_bus.get_stats(),
        }
    )
