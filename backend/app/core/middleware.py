"""
FastAPI middleware stack:
1. RequestIDMiddleware  — inject unique request_id into every request
2. RequestLoggingMiddleware — log request/response with timing
3. Global exception handler — convert AppException → JSON response
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
    Order matters: last-added runs first (LIFO).
    """
    settings = get_settings()

    # 1. CORS — must be outermost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # 3. Request ID injection (innermost — runs first)
    app.add_middleware(RequestIDMiddleware)
