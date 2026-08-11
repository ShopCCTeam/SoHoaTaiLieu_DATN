"""Celery worker package."""

from __future__ import annotations

from app.worker.celery_app import celery_app
from app.worker.tasks import process_document_task

__all__ = ["celery_app", "process_document_task"]
