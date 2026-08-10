"""Pydantic Settings (12-factor). Load từ env + .env.

Quy tắc:
- Tất cả config có default an toàn ở dev.
- Production phải set POSTGRES_PASSWORD, JWT_SECRET, MINIO_SECRET_KEY
  qua secret manager (KHÔNG commit .env).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — bind to env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_name: str = "ctsv-api"
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    app_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
    )

    # ---- API ----
    api_base_url: str = "http://localhost:8000"
    api_prefix: str = "/api/v1"

    # ---- Database ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ctsv"
    postgres_user: str = "ctsv_app"
    postgres_password: SecretStr = Field(default=SecretStr("change-me"))
    postgres_timeout_seconds: int = 5

    # ---- Redis (Celery broker) ----
    redis_url: str = "redis://localhost:6379/0"

    # ---- MinIO ----
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: SecretStr = Field(default=SecretStr("minioadmin"))
    minio_bucket: str = "ctsv-documents"
    minio_secure: bool = False

    # ---- Auth ----
    jwt_secret: SecretStr = Field(
        default=SecretStr("dev-only-change-in-production-use-32-plus-bytes")
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_ttl_seconds: int = 15 * 60  # 15 minutes
    jwt_refresh_token_ttl_seconds: int = 7 * 24 * 60 * 60  # 7 days
    refresh_cookie_name: str = "rt"
    refresh_cookie_path: str = "/api/v1/auth"
    refresh_cookie_secure: bool = False  # True in production (HTTPS)

    # ---- OCR ----
    ocr_default_confidence_threshold: float = 0.9
    ocr_default_engine: Literal["paddleocr", "tesseract"] = "paddleocr"

    # ---- Derived URL ----
    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:"
            f"{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins(self) -> list[str]:
        return self.app_cors_origins

    @field_validator("app_cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        """Allow comma-separated string for CORS origins."""
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    # ---- Seed guard ----
    @property
    def allow_seed(self) -> bool:
        """Cho phép seed chỉ ở development/test."""
        return self.app_env in ("development", "test")

    # ---- Fail-closed checks (D9) ----
    def validate_production(self) -> list[str]:
        """Return list of warnings/errors nếu production config không an toàn."""
        issues: list[str] = []

        # JWT secret phải được override ở production
        default_jwt = "dev-only-change-in-production-use-32-plus-bytes"
        if self.app_env == "production":
            if self.jwt_secret.get_secret_value() == default_jwt:
                issues.append(
                    "JWT_SECRET is using default value in production. "
                    "Set APP_ENV=production and JWT_SECRET to a strong secret."
                )
            if not self.postgres_password.get_secret_value() or \
               self.postgres_password.get_secret_value() == "change-me":
                issues.append(
                    "POSTGRES_PASSWORD is using default value in production."
                )
            if self.refresh_cookie_secure is False:
                issues.append(
                    "refresh_cookie_secure is False in production. "
                    "Set REFRESH_COOKIE_SECURE=true when deploying behind HTTPS."
                )

        return issues


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings. `lru_cache` để test override dễ."""
    return Settings()
