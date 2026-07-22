"""
Request-level middleware for logging, request IDs, and timing.
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

import structlog

from app.middleware.logging import get_logger

logger = get_logger("request")


class RequestMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    - Generates a unique request ID for every request
    - Logs request method, path, status code, and latency
    - Attaches X-Request-ID to response headers
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        # Bind context for structlog so all logs within this request carry the ID
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        logger.info(
            "request_started",
            method=request.method,
            path=str(request.url.path),
            client=request.client.host if request.client else "unknown",
        )

        response = await call_next(request)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_completed",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            latency_ms=latency_ms,
        )

        return response
