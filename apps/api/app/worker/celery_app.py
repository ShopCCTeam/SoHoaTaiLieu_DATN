"""Celery Worker Instance & Configuration."""

from __future__ import annotations

from celery import Celery  # type: ignore[import-untyped]

from app.core.config import Settings, get_settings

celery_app = Celery("ctsv_worker")


def configure_celery(settings: Settings | None = None) -> None:
    st = settings or get_settings()
    is_eager = st.celery_task_always_eager or st.app_env == "test"

    celery_app.conf.update(
        broker_url=st.celery_broker_url,
        result_backend="cache+memory://" if is_eager else st.celery_result_backend,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=st.celery_task_time_limit,
        task_soft_time_limit=st.celery_task_soft_time_limit,
        result_expires=86400,  # 24h
        worker_prefetch_multiplier=1,
        task_always_eager=is_eager,
        task_eager_propagates=True,
        task_store_eager_result=False,
        task_routes={
            "app.worker.tasks.process_document_task": {"queue": "documents"},
        },
    )


configure_celery()
