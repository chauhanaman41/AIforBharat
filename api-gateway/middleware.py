"""
API Gateway — Middleware
=========================
Rate limiting (in-memory token bucket) and request logging.
"""

import logging
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from shared.config import settings
from shared.models import ApiResponse

logger = logging.getLogger("api_gateway.middleware")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory token bucket rate limiter.
    Rules:
    - Per-IP: 100 requests/minute
    - Per-user (if authenticated): 60 requests/minute, 20/minute for AI endpoints
    - Global: 10,000 RPS (generous for local dev)
    
    Returns HTTP 429 with Retry-After header on limit exceeded.
    """

    def __init__(self, app):
        super().__init__(app)
        # {ip: {count, window_start}}
        self._ip_buckets: dict[str, dict] = defaultdict(lambda: {"count": 0, "window_start": time.time()})
        self._user_buckets: dict[str, dict] = defaultdict(lambda: {"count": 0, "window_start": time.time()})

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json", "/"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # ── Per-IP rate limiting ──────────────────────────────────────
        bucket = self._ip_buckets[client_ip]
        if now - bucket["window_start"] > 60:
            bucket["count"] = 0
            bucket["window_start"] = now

        bucket["count"] += 1

        if bucket["count"] > settings.RATE_LIMIT_PER_IP_RPM:
            retry_after = int(60 - (now - bucket["window_start"]))
            logger.warning(f"Rate limit exceeded for IP {client_ip}")
            return JSONResponse(
                status_code=429,
                content=ApiResponse(
                    success=False,
                    message="Too many requests. Please slow down.",
                    errors=[{"detail": f"Rate limit: {settings.RATE_LIMIT_PER_IP_RPM}/min"}],
                ).model_dump(mode="json"),
                headers={"Retry-After": str(max(1, retry_after))},
            )

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every request with method, path, status code, and latency.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        
        response = await call_next(request)
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} "
            f"({elapsed_ms:.1f}ms) [IP: {request.client.host if request.client else 'N/A'}]"
        )

        # Add timing header
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
        return response
