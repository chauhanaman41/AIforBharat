"""
API Gateway — Middleware
=========================
Rate limiting (in-memory token bucket + burst protection) and request logging.
"""

import logging
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from shared.config import settings
from shared.models import ApiResponse, ErrorCode, make_error

logger = logging.getLogger("api_gateway.middleware")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory rate limiter with two layers:

    1. Per-IP per-minute: 100 requests/minute (configurable)
    2. Per-IP per-second burst: 10 requests/second (UI loop protection)

    Returns HTTP 429 with Retry-After header and X-Trace-ID on limit exceeded.
    """

    def __init__(self, app):
        super().__init__(app)
        # Per-minute buckets: {ip: {count, window_start}}
        self._ip_buckets: dict[str, dict] = defaultdict(lambda: {"count": 0, "window_start": time.time()})
        # Per-second burst buckets: {ip: {count, window_start}}
        self._burst_buckets: dict[str, dict] = defaultdict(lambda: {"count": 0, "window_start": time.time()})

    async def dispatch(self, request: Request, call_next) -> Response:
        # Let CORS preflight requests pass through without rate limiting
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json", "/"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        trace_id = getattr(request.state, "trace_id", "") or getattr(request.state, "request_id", "")

        # ── Per-second burst protection (UI infinite loop guard) ──────
        burst = self._burst_buckets[client_ip]
        if now - burst["window_start"] > 1.0:
            burst["count"] = 0
            burst["window_start"] = now

        burst["count"] += 1

        if burst["count"] > settings.RATE_LIMIT_BURST_PER_SECOND:
            logger.warning(f"Burst rate limit exceeded for IP {client_ip} ({burst['count']} req/s) [trace={trace_id}]")
            return JSONResponse(
                status_code=429,
                content=ApiResponse(
                    success=False,
                    message="Too many requests per second. Possible infinite loop detected.",
                    errors=[make_error(
                        ErrorCode.BURST_LIMIT,
                        f"Burst limit: max {settings.RATE_LIMIT_BURST_PER_SECOND} requests/second",
                    )],
                    trace_id=trace_id,
                ).model_dump(mode="json"),
                headers={"Retry-After": "1", "X-Trace-ID": trace_id},
            )

        # ── Per-IP per-minute rate limiting ───────────────────────────
        bucket = self._ip_buckets[client_ip]
        if now - bucket["window_start"] > 60:
            bucket["count"] = 0
            bucket["window_start"] = now

        bucket["count"] += 1

        if bucket["count"] > settings.RATE_LIMIT_PER_IP_RPM:
            retry_after = int(60 - (now - bucket["window_start"]))
            logger.warning(f"Rate limit exceeded for IP {client_ip} [trace={trace_id}]")
            return JSONResponse(
                status_code=429,
                content=ApiResponse(
                    success=False,
                    message="Too many requests. Please slow down.",
                    errors=[make_error(
                        ErrorCode.RATE_LIMIT,
                        f"Rate limit: {settings.RATE_LIMIT_PER_IP_RPM} requests/minute",
                    )],
                    trace_id=trace_id,
                ).model_dump(mode="json"),
                headers={"Retry-After": str(max(1, retry_after)), "X-Trace-ID": trace_id},
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
