"""Domain exceptions + RFC 7807 Problem Details response."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from structlog import get_logger

from app.core.constants import PROBLEM_TYPE_BASE, REQUEST_ID_HEADER

_logger = get_logger(__name__)


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details. Match FE shape (apps/web/lib/api/types.ts)."""

    type: str
    title: str
    status: int
    detail: str | None = None
    code: str
    request_id: str
    errors: list[dict[str, str]] | None = None


# ---- Recognised codes ----
class ErrorCode:
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    IDEMPOTENCY_KEY_MISMATCH = "IDEMPOTENCY_KEY_MISMATCH"
    RATE_LIMIT = "RATE_LIMIT"
    CONFLICT = "CONFLICT"
    INTERNAL = "INTERNAL"
    # Auth codes (Phase 1.1)
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_USER_INACTIVE = "AUTH_USER_INACTIVE"
    AUTH_USER_NOT_FOUND = "AUTH_USER_NOT_FOUND"
    AUTH_USER_DISABLED = "AUTH_USER_DISABLED"
    AUTH_MISSING_TOKEN = "AUTH_MISSING_TOKEN"  # noqa: S105
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"  # noqa: S105
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"  # noqa: S105
    AUTH_REFRESH_INVALID = "AUTH_REFRESH_INVALID"
    AUTH_REFRESH_EXPIRED = "AUTH_REFRESH_EXPIRED"
    AUTH_REFRESH_REUSE_DETECTED = "AUTH_REFRESH_REUSE_DETECTED"
    AUTH_CSRF_ORIGIN_REJECTED = "AUTH_CSRF_ORIGIN_REJECTED"
    AUTH_CSRF_ORIGIN_ABSENT = "AUTH_CSRF_ORIGIN_ABSENT"


# ---- Auth error codes (Phase 1.1) ----
AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
AUTH_USER_INACTIVE = "AUTH_USER_INACTIVE"
AUTH_REFRESH_INVALID = "AUTH_REFRESH_INVALID"
AUTH_REFRESH_EXPIRED = "AUTH_REFRESH_EXPIRED"
AUTH_REFRESH_REUSE_DETECTED = "AUTH_REFRESH_REUSE_DETECTED"
AUTH_CSRF_ORIGIN_REJECTED = "AUTH_CSRF_ORIGIN_REJECTED"
AUTH_CSRF_ORIGIN_ABSENT = "AUTH_CSRF_ORIGIN_ABSENT"


class ApiError(Exception):
    """Base exception carrying coded problem details."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        title: str,
        detail: str | None = None,
        request_id: str,
        errors: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(title)
        self.status_code = status_code
        self.code = code
        self.title = title
        self.detail = detail
        self.request_id = request_id
        self.errors = errors

    def to_problem(self) -> ProblemDetail:
        return ProblemDetail(
            type=f"{PROBLEM_TYPE_BASE}/{self.code.lower()}",
            title=self.title,
            status=self.status_code,
            detail=self.detail,
            code=self.code,
            request_id=self.request_id,
            errors=self.errors,
        )


# ---- Convenience builders ----

def unauthorized(
    detail: str | None = None,
    request_id: str = "",
    *,
    code: str = ErrorCode.UNAUTHORIZED,
) -> ApiError:
    """401 Unauthorized. Có thể override `code` cho các nguyên nhân cụ thể
    (vd: AUTH_INVALID_CREDENTIALS, AUTH_TOKEN_EXPIRED)."""
    return ApiError(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code=code,
        title="Chưa xác thực",
        detail=detail,
        request_id=request_id,
    )


def forbidden(
    detail: str | None = None,
    request_id: str = "",
    *,
    code: str = ErrorCode.FORBIDDEN,
) -> ApiError:
    return ApiError(
        status_code=status.HTTP_403_FORBIDDEN,
        code=code,
        title="Không đủ quyền",
        detail=detail,
        request_id=request_id,
    )


def not_found(
    detail: str | None = None,
    request_id: str = "",
    *,
    code: str = ErrorCode.NOT_FOUND,
) -> ApiError:
    return ApiError(
        status_code=status.HTTP_404_NOT_FOUND,
        code=code,
        title="Không tìm thấy",
        detail=detail,
        request_id=request_id,
    )


def validation_error(
    errors: list[dict[str, str]],
    request_id: str,
    detail: str | None = None,
) -> ApiError:
    return ApiError(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code=ErrorCode.VALIDATION_ERROR,
        title="Dữ liệu không hợp lệ",
        detail=detail,
        request_id=request_id,
        errors=errors,
    )


def conflict(detail: str, request_id: str) -> ApiError:
    return ApiError(
        status_code=status.HTTP_409_CONFLICT,
        code=ErrorCode.CONFLICT,
        title="Xung đột",
        detail=detail,
        request_id=request_id,
    )


def idempotency_mismatch(request_id: str) -> ApiError:
    return ApiError(
        status_code=status.HTTP_409_CONFLICT,
        code=ErrorCode.IDEMPOTENCY_KEY_MISMATCH,
        title="Idempotency-Key không khớp",
        detail="Key trùng nhưng request body khác nhau.",
        request_id=request_id,
    )


def internal_error(request_id: str) -> ApiError:
    return ApiError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ErrorCode.INTERNAL,
        title="Lỗi hệ thống",
        detail="Đã có lỗi xảy ra. Vui lòng thử lại sau.",
        request_id=request_id,
    )


# ---- Handlers ----

def _problem_response(problem: ProblemDetail) -> JSONResponse:
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
        headers={REQUEST_ID_HEADER: problem.request_id},
    )


def _request_id_from(request: Request) -> str:
    return getattr(request.state, "request_id", "") or "unknown"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        if exc.request_id == "":
            exc.request_id = _request_id_from(request)
        _logger.warning(
            "api_error",
            code=exc.code,
            status=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            request_id=exc.request_id,
        )
        return _problem_response(exc.to_problem())

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = _request_id_from(request)
        errors = [
            {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        err = validation_error(errors, request_id)
        return _problem_response(err.to_problem())

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _request_id_from(request)
        _logger.exception("unhandled_exception", request_id=request_id, error=str(exc))
        err = internal_error(request_id)
        return _problem_response(err.to_problem())
