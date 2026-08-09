"""Unit tests cho RFC 7807 problem builders."""

from __future__ import annotations

from app.core.errors import (
    ApiError,
    ErrorCode,
    forbidden,
    idempotency_mismatch,
    internal_error,
    not_found,
    unauthorized,
    validation_error,
)


def test_unauthorized_problem() -> None:
    err = unauthorized(detail="Token expired", request_id="req-123")
    assert err.status_code == 401
    assert err.code == ErrorCode.UNAUTHORIZED
    assert err.detail == "Token expired"
    assert err.request_id == "req-123"
    problem = err.to_problem()
    assert problem.type == "https://api.example.edu.vn/problems/unauthorized"
    assert problem.title == "Chưa xác thực"


def test_validation_error_includes_field_errors() -> None:
    errors = [
        {"field": "body.email", "message": "field required"},
        {"field": "body.password", "message": "min length 8"},
    ]
    err = validation_error(errors, request_id="req-456")
    assert err.status_code == 422
    assert err.code == ErrorCode.VALIDATION_ERROR
    assert err.errors == errors


def test_forbidden_default_message() -> None:
    err = forbidden(request_id="req-789")
    assert err.status_code == 403
    assert err.code == ErrorCode.FORBIDDEN


def test_not_found() -> None:
    err = not_found(detail="Document not found", request_id="req-aaa")
    assert err.status_code == 404
    assert err.code == ErrorCode.NOT_FOUND


def test_idempotency_mismatch() -> None:
    err = idempotency_mismatch(request_id="req-bbb")
    assert err.status_code == 409
    assert err.code == ErrorCode.IDEMPOTENCY_KEY_MISMATCH


def test_internal_error_no_detail_leak() -> None:
    """Internal error không được leak thông tin chi tiết."""
    err = internal_error(request_id="req-ccc")
    assert err.status_code == 500
    assert err.code == ErrorCode.INTERNAL
    # detail phải là message chung chung, không lộ stack trace.
    assert "stacktrace" not in (err.detail or "").lower()


def test_api_error_is_exception() -> None:
    """ApiError phải là Exception để có thể raise."""
    assert issubclass(ApiError, Exception)
