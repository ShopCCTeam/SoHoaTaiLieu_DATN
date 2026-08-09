"""Request ID middleware + structlog context binding.

Sử dụng UUID v7 (RFC 9562) — sortable, có timestamp cho debugging.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import REQUEST_ID_HEADER


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Đọc / generate request_id, set vào context log + response header.

    Phase 0 dùng UUID v4 — Phase 1+ chuyển sang v7 (sortable) khi `uuid.uuid7()`
    có sẵn trong Python 3.14+.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        # Bind request_id vào structlog context — mọi log trong request này
        # sẽ tự động có request_id.
        structlog.contextvars.bind_contextvars(request_id=request_id)

        try:
            response: Response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
