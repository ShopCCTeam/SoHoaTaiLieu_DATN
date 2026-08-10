"""FastAPI application factory.

Contract-first: route handler signatures phải khớp `docs/api/openapi.yaml`.
Khi generate OpenAPI runtime, dùng `app.openapi()` rồi diff với contract.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from structlog import get_logger

from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.modules.auth.router import router as auth_router

_logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory. Khởi tạo FastAPI app + register handlers/middleware."""
    settings = settings or get_settings()
    configure_logging(settings.app_log_level)

    # operation_id ngắn gọn cho OpenAPI (mặc định FastAPI sinh từ function name).
    app = FastAPI(
        title="Hệ Thống Số Hoá Tài Liệu CTSV — REST API",
        version="1.0.0-draft",
        description=(
            "Backend API. Contract chuẩn: docs/api/openapi.yaml. "
            "Mọi sửa endpoint phải cập nhật OpenAPI trước."
        ),
        default_response_class=JSONResponse,
        generate_unique_id_function=_generate_unique_id,
    )

    # ---- Middleware (order: request-id đầu tiên để mọi log có request_id) ----
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # ---- Exception handlers (RFC 7807) ----
    register_exception_handlers(app)

    # ---- Health checks ----
    @app.get("/health/live", tags=["health"])
    async def health_live() -> dict[str, str]:
        """Liveness probe — service đang chạy."""
        return {"status": "alive"}

    @app.get("/health/ready", tags=["health"])
    async def health_ready() -> JSONResponse:
        """Readiness probe — check Postgres connectivity (D10)."""
        settings = get_settings()
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            engine = create_async_engine(
                settings.postgres_url,
                echo=False,
                pool_pre_ping=True,
                connect_timeout=settings.postgres_timeout_seconds,
            )
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            return JSONResponse(
                content={"status": "ready", "postgres": "ok"},
                headers={"X-Request-ID": "ready-check"},
            )
        except Exception:
            _logger.error("health_ready_check_failed", postgres=settings.postgres_host)
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "postgres": "unavailable"},
                headers={"X-Request-ID": "ready-check"},
            )

    # ---- Routers ----
    # Tất cả domain routes đi qua api_prefix để dễ version sau này.
    app.include_router(auth_router, prefix=settings.api_prefix)

    # ---- Root ----
    @app.get("/", tags=["meta"], include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": "1.0.0-draft",
            "docs": "/docs",
        }

    _logger.info("fastapi_app_created", env=settings.app_env)
    return app


def _generate_unique_id(route: APIRoute) -> str:
    """Generate short, stable operation_id for OpenAPI.

    Format: <method>_<path>, dùng để client/server dễ reference.
    """
    method = route.methods.copy().pop().lower()
    clean_path = (
        route.path.replace("/", "_").replace("{", "").replace("}", "").strip("_")
    )
    return f"{method}_{clean_path}"


# Convenience export — chỉ dùng cho uvicorn CLI trực tiếp.
app = create_app()


__all__ = ["create_app", "app"]
