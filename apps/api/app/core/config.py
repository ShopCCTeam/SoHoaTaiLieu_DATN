"""Pydantic Settings (12-factor). Load từ env + .env.

Quy tắc:
- Tất cả config có default an toàn ở dev (khớp docker-compose.yml).
- Production/staging phải set POSTGRES_PASSWORD, JWT_SECRET, MINIO_SECRET_KEY
  qua secret manager (KHÔNG commit .env).
- validate_production() fail-closed: reject deployment nếu có config yếu.
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
    postgres_password: SecretStr = Field(default=SecretStr("ctsv_dev_password"))
    postgres_timeout_seconds: int = 5

    # ---- Redis (Celery broker) ----
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_documents_queue: str = "documents"
    celery_task_always_eager: bool = False
    celery_task_time_limit: int = 300
    celery_task_soft_time_limit: int = 240

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
    trust_proxy_headers: bool = False  # True if behind reverse proxy (X-Forwarded-For)

    # ---- OCR ----
    ocr_default_confidence_threshold: float = 0.9
    ocr_default_engine: Literal["paddleocr", "tesseract"] = "paddleocr"
    ocr_render_dpi: int = Field(default=300, ge=72, le=600)
    ocr_text_layer_min_characters: int = Field(default=50, ge=1, le=10_000)
    ocr_preprocess_enabled: bool = False
    ocr_preprocess_deskew: bool = True
    ocr_preprocess_denoise_kernel_size: int = Field(default=3, ge=1, le=31)
    ocr_preprocess_binarize: bool = True
    ocr_preprocess_adaptive_threshold_block_size: int = Field(default=31, ge=3, le=255)
    ocr_preprocess_adaptive_threshold_c: int = Field(default=11, ge=-255, le=255)

    # ---- Embedding & RAG ----
    embedding_provider: Literal["bge-m3", "mock"] = "mock"
    embedding_api_url: str = "http://localhost:11434/api/embed"
    embedding_model_name: str = "bge-m3"
    embedding_ollama_keep_alive: str = "5m"

    # ---- RAG grounding ----
    rag_vector_score_threshold: float = Field(default=0.6, ge=0.0, le=1.0)

    # ---- LLM Chatbot ----
    llm_provider: Literal["ollama", "mock"] = "mock"
    llm_ollama_base_url: str = "http://localhost:11434"
    llm_ollama_model_name: str = "qwen2.5:7b"
    llm_ollama_keep_alive: str = "5m"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1000
    llm_timeout_seconds: int = 30

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

    # ---- Cookie Secure ----
    @property
    def cookie_secure(self) -> bool:
        """Secure flag cho Set-Cookie.

        Bật nếu app_env ∈ {production, staging} (HTTPS bắt buộc).
        Override bằng refresh_cookie_secure (cho phép True ở staging test).
        """
        if self.app_env in {"production", "staging"}:
            return True
        return self.refresh_cookie_secure

    # ---- Seed guard ----
    @property
    def allow_seed(self) -> bool:
        """Cho phép seed chỉ ở development/test."""
        return self.app_env in ("development", "test")

    # ---- Fail-closed checks (D9) ----
    def validate_production(self) -> list[str]:
        """Return list of warnings/errors nếu production/staging config không an toàn.

        Fail-closed: rejects deployment nếu có config yếu. ADR D9.
        Áp dụng cho {production, staging} — không phải development/test.
        """
        issues: list[str] = []

        # JWT secret: phải khác default VÀ đủ dài
        default_jwt = "dev-only-change-in-production-use-32-plus-bytes"
        if self.app_env in {"production", "staging"}:
            jwt_val = self.jwt_secret.get_secret_value()
            if jwt_val == default_jwt:
                issues.append(
                    "JWT_SECRET is using default value in production/staging. "
                    "Set APP_ENV=production and JWT_SECRET to a strong secret."
                )
            elif len(jwt_val) < 32:
                issues.append(
                    f"JWT_SECRET is only {len(jwt_val)} characters. "
                    "Minimum 32 bytes required (HS256 recommendation)."
                )

        # Postgres password: phải khác default dev password
        if self.app_env in {"production", "staging"}:
            pg_val = self.postgres_password.get_secret_value()
            if not pg_val or pg_val == "ctsv_dev_password":
                issues.append(
                    "POSTGRES_PASSWORD is using dev default value in production/staging. "
                    "Set POSTGRES_PASSWORD to a production-grade secret."
                )

        # MinIO secret key: không được dùng default
        if self.app_env in {"production", "staging"}:
            if self.minio_secret_key.get_secret_value() == "minioadmin":
                issues.append(
                    "MINIO_SECRET_KEY is using default value. "
                    "Set MINIO_SECRET_KEY to a production-grade secret."
                )

        return issues


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings. `lru_cache` để test override dễ."""
    return Settings()
