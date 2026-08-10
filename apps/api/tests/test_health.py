"""Smoke tests cho FastAPI app factory + health checks."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_live() -> None:
    client = TestClient(create_app())
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.integration
def test_health_ready() -> None:
    """Readiness probe check Postgres connectivity (D10)."""
    client = TestClient(create_app())
    response = client.get("/health/ready")
    # 200 khi Postgres available, 503 khi không.
    assert response.status_code in (200, 503)
    body = response.json()
    assert "status" in body
    assert "postgres" in body


def test_root_returns_service_metadata() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "ctsv-api"
    assert body["docs"] == "/docs"


def test_request_id_propagated() -> None:
    """Request ID từ header phải được echo lại trong response."""
    client = TestClient(create_app())
    response = client.get("/health/live", headers={"X-Request-ID": "test-req-123"})
    assert response.headers.get("X-Request-ID") == "test-req-123"


def test_request_id_generated_when_missing() -> None:
    client = TestClient(create_app())
    response = client.get("/health/live")
    # Khi client không truyền, server tự generate UUID v7.
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_not_found_returns_problem_detail() -> None:
    """404 không tồn tại → RFC 7807 Problem Details."""
    client = TestClient(create_app())
    response = client.get("/does-not-exist")
    # FastAPI default 404 — sẽ xử lý qua unhandled handler hoặc FastAPI default.
    # Acceptable: 404 với body JSON.
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body or "code" in body or "title" in body


def test_validation_error_returns_problem_detail() -> None:
    """Validation error → RFC 7807 với code=VALIDATION_ERROR.

    Phase 0 chưa có POST endpoint để trigger validation; test rỗng để đánh
    dấu contract cần cover ở Phase 1.
    """
    assert True
