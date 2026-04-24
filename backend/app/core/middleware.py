"""
FastAPI middleware stack:
1. SecurityHeadersMiddleware — add security headers to every response
2. RateLimitMiddleware       — Redis-backed sliding window rate limiter
3. RequestIDMiddleware       — inject unique request_id into every request
4. RequestLoggingMiddleware  — log request/response with timing
5. Global exception handlers — convert AppException → JSON response

Rate limiting strategy:
- Auth endpoints (/api/v1/auth/*): stricter limit (default 10 req/min)
- All other endpoints: general limit (default 120 req/min)
- Key: IP address from X-Forwarded-For or client.host
- Fail-open: if Redis is unavailable, all requests pass through
- Algorithm: Fixed window counter (per minute) — simple & production-safe MVP
"""

import time
import uuid
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import get_settings
from app.core.exceptions import AppException

log = structlog.get_logger(__name__)


# ------------------------------------------------------------------ #
# Security Headers Middleware
# ------------------------------------------------------------------ #

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security-hardening HTTP headers to every response.
    These headers protect against common browser-based attacks.
    """

    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-XSS-Protection": "1; mode=block",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for header, value in self.HEADERS.items():
            response.headers[header] = value
        return response


# ------------------------------------------------------------------ #
# Rate Limit Middleware (Redis-backed, fail-open)
# ------------------------------------------------------------------ #

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding fixed-window rate limiter using Redis INCR + EXPIRE.

    Algorithm:
    1. Build key: rate_limit:{ip}:{endpoint_type}:{current_minute}
    2. INCR the counter
    3. If counter == 1 (first hit), set TTL to 60 seconds
    4. If counter > limit → return 429

    Fail-open: if Redis is unavailable, all requests pass through
    and a warning is logged.
    """

    # Paths that get the stricter auth rate limit
    AUTH_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()

        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)

        # Lazy import to avoid circular dependency
        from app.core.redis import get_redis

        redis = await get_redis()
        if redis is None:
            # Fail-open: Redis unavailable, let request through
            return await call_next(request)

        # Identify client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
            request.client.host if request.client else "unknown"
        )

        # Determine which limit to apply
        is_auth = request.url.path in self.AUTH_PATHS
        limit = settings.RATE_LIMIT_AUTH_RPM if is_auth else settings.RATE_LIMIT_GENERAL_RPM
        endpoint_type = "auth" if is_auth else "general"

        # Fixed-window key: changes every minute
        current_minute = int(time.time() // 60)
        redis_key = f"rate_limit:{client_ip}:{endpoint_type}:{current_minute}"

        try:
            from redis.exceptions import RedisError
            # Atomic INCR
            count = await redis.incr(redis_key)
            if count == 1:
                # First request this minute — set TTL
                await redis.expire(redis_key, 60)

            if count > limit:
                log.warning(
                    "rate_limit_exceeded",
                    ip=client_ip,
                    endpoint_type=endpoint_type,
                    count=count,
                    limit=limit,
                )
                retry_after = 60 - (int(time.time()) % 60)
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Terlalu banyak permintaan. Coba lagi dalam {retry_after} detik.",
                        },
                    },
                    headers={"Retry-After": str(retry_after)},
                )
        except Exception as exc:
            # Fail-open on any Redis error
            log.warning("rate_limit_redis_error", error=str(exc))

        return await call_next(request)


# ------------------------------------------------------------------ #
# Request ID Middleware
# ------------------------------------------------------------------ #

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Generates a unique UUID for every incoming request and:
    - Stores it in request.state for access by exception handlers
    - Binds it to structlog context (appears in all log lines)
    - Adds it to the response headers as X-Request-ID
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())

        # Store in request.state so exception handlers can access it
        request.state.request_id = request_id

        # Bind to structlog for automatic inclusion in all log lines
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ------------------------------------------------------------------ #
# Request Logging Middleware
# ------------------------------------------------------------------ #

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every request with method, path, status code, and duration.
    Skips health-check endpoint to reduce noise.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path == "/health":
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


# ------------------------------------------------------------------ #
# Error response helpers
# ------------------------------------------------------------------ #

def _get_request_id(request: Request) -> str | None:
    """Safely extract request_id from request.state."""
    return getattr(request.state, "request_id", None)


def _error_body(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id,
        },
    }


# ------------------------------------------------------------------ #
# Global Exception Handlers
# ------------------------------------------------------------------ #

def _sanitize_validation_errors(errors: list) -> list:
    """
    Pydantic v2 may embed non-JSON-serializable objects (e.g. ValueError)
    inside errors()[*]['ctx']['error']. Convert those to strings.
    """
    sanitized = []
    for err in errors:
        safe = dict(err)
        if "ctx" in safe and isinstance(safe["ctx"], dict):
            safe["ctx"] = {
                k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                for k, v in safe["ctx"].items()
            }
        sanitized.append(safe)
    return sanitized


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        request_id = _get_request_id(request)
        log.warning(
            "app_exception",
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details, request_id),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Handles FastAPI's RequestValidationError (malformed request body,
        missing query params, wrong types, etc.).
        This is the exception FastAPI actually raises — not raw pydantic.ValidationError.
        """
        request_id = _get_request_id(request)
        safe_errors = _sanitize_validation_errors(exc.errors())
        log.warning("validation_error", errors=safe_errors)
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "VALIDATION_ERROR",
                "Input tidak valid. Periksa kembali data yang Anda kirim.",
                {"errors": safe_errors},
                request_id,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        request_id = _get_request_id(request)
        log.exception("unhandled_exception", error_type=type(exc).__name__, error=repr(exc))
        return JSONResponse(
            status_code=500,
            content=_error_body(
                "INTERNAL_SERVER_ERROR",
                "Terjadi kesalahan pada server. Silakan coba lagi.",
                request_id=request_id,
            ),
        )


# ------------------------------------------------------------------ #
# Register all middleware on the app
# ------------------------------------------------------------------ #

def register_middleware(app: FastAPI) -> None:
    """
    Add all middleware to the FastAPI app.
    Order matters: last-added runs first (LIFO stack).

    Execution order (outermost → innermost):
    1. CORS
    2. SecurityHeaders
    3. RateLimit
    4. RequestLogging
    5. RequestID  ← innermost, runs first
    """
    settings = get_settings()

    # 1. CORS — must be outermost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # 2. Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # 3. Rate limiting (Redis-backed, fail-open)
    app.add_middleware(RateLimitMiddleware)

    # 4. Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # 5. Request ID injection (innermost — runs first)
    app.add_middleware(RequestIDMiddleware)
