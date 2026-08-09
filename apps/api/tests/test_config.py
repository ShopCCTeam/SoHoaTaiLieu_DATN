"""Unit tests cho Pydantic Settings."""

from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings


def test_default_settings_for_dev() -> None:
    """Default settings phải an toàn cho dev (localhost, placeholder secret)."""
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
        Settings(app_env="invalid")  # type: ignore[call-arg]
