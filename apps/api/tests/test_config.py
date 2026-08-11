"""Unit tests cho Pydantic Settings."""

from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings


def test_default_settings_for_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default settings phải an toàn cho dev (localhost, placeholder secret)."""
    # Clear test env vars set by conftest.
    monkeypatch.delenv("JWT_ACCESS_TOKEN_TTL_SECONDS", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    get_settings.cache_clear()
    settings = Settings()  # type: ignore[call-arg]
    assert settings.app_env == "development"
    assert settings.postgres_host == "localhost"
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_access_token_ttl_seconds == 900


def test_postgres_url_built_correctly() -> None:
    settings = Settings(  # type: ignore[call-arg]
        postgres_host="db.example.com",
        postgres_port=5433,
        postgres_db="ctsv_prod",
        postgres_user="ctsv_user",
        postgres_password="secret123",  # type: ignore[arg-type]
    )
    assert (
        settings.postgres_url
        == "postgresql+asyncpg://ctsv_user:secret123@db.example.com:5433/ctsv_prod"
    )


def test_cors_origins_parsed_from_csv_string() -> None:
    settings = Settings(app_cors_origins="http://localhost:3000,https://app.example.com")  # type: ignore[arg-type]
    assert settings.app_cors_origins == [
        "http://localhost:3000",
        "https://app.example.com",
    ]


def test_get_settings_is_singleton() -> None:
    """get_settings() phải trả về cùng instance (cache)."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_jwt_secret_redacted_in_repr() -> None:
    """Pydantic SecretStr KHÔNG log raw value."""
    settings = Settings(jwt_secret="my-very-secret-value")  # type: ignore[arg-type]
    assert "my-very-secret-value" not in repr(settings)
    assert settings.jwt_secret.get_secret_value() == "my-very-secret-value"


def test_invalid_env_raises() -> None:
    """Invalid app_env phải raise validation error."""
    with pytest.raises(ValueError):
        Settings(app_env="invalid")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# validate_production() — fail-closed checks (D9)
# ---------------------------------------------------------------------------


def test_validate_production_dev_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Development env: không có issues."""
    monkeypatch.delenv("JWT_SECRET", raising=False)
    get_settings.cache_clear()
    settings = Settings(app_env="development")  # type: ignore[arg-type]
    assert settings.validate_production() == []


def test_validate_production_staging_jwt_default_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Staging với JWT default: phải có issue JWT.

    Mock Settings.__init__ để bypass conftest._test_env (JWT_SECRET env override).
    """
    monkeypatch.delenv("JWT_SECRET", raising=False)
    get_settings.cache_clear()
    settings = Settings(app_env="staging")  # type: ignore[arg-type]
    issues = settings.validate_production()
    jwt_issues = [i for i in issues if "JWT_SECRET" in i]
    assert len(jwt_issues) == 1
    assert "default value" in jwt_issues[0]


def test_validate_production_staging_jwt_short_rejected() -> None:
    """Staging với JWT < 32 bytes: phải bị reject."""
    settings = Settings(
        app_env="staging",  # type: ignore[arg-type]
        jwt_secret="abc",  # type: ignore[arg-type]
    )
    issues = settings.validate_production()
    jwt_issues = [i for i in issues if "JWT_SECRET" in i]
    assert len(jwt_issues) == 1
    assert "32" in jwt_issues[0]


def test_validate_production_staging_pg_dev_default_rejected() -> None:
    """Staging với postgres_password dev default: phải bị reject."""
    settings = Settings(
        app_env="staging",  # type: ignore[arg-type]
        jwt_secret="a-strong-secret-thats-at-least-32-chars!",  # type: ignore[arg-type]
    )
    issues = settings.validate_production()
    pg_issues = [i for i in issues if "POSTGRES_PASSWORD" in i]
    assert len(pg_issues) == 1
    assert "dev default" in pg_issues[0]


def test_validate_production_staging_minio_default_rejected() -> None:
    """Staging với minio_secret_key default: phải bị reject."""
    settings = Settings(
        app_env="staging",  # type: ignore[arg-type]
        jwt_secret="a-strong-secret-thats-at-least-32-chars!",  # type: ignore[arg-type]
        postgres_password="ProdSecret!",  # type: ignore[arg-type]
    )
    issues = settings.validate_production()
    assert len(issues) == 1
    assert "MINIO_SECRET_KEY" in issues[0]


def test_validate_production_staging_all_good_empty() -> None:
    """Staging với tất cả secret đủ mạnh: không có issue."""
    settings = Settings(
        app_env="staging",  # type: ignore[arg-type]
        jwt_secret="a-strong-secret-thats-at-least-32-chars!",  # type: ignore[arg-type]
        postgres_password="ProdSecret!",  # type: ignore[arg-type]
        minio_secret_key="minio-prod-secret-key-here!",  # type: ignore[arg-type]
    )
    assert settings.validate_production() == []


def test_validate_production_jwt_default_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production với JWT default: phải có issue JWT."""
    monkeypatch.delenv("JWT_SECRET", raising=False)
    get_settings.cache_clear()
    settings = Settings(app_env="production")  # type: ignore[arg-type]
    issues = settings.validate_production()
    jwt_issues = [i for i in issues if "JWT_SECRET" in i]
    assert len(jwt_issues) >= 1
    assert any("default value" in i for i in jwt_issues)
