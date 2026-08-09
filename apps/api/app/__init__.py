"""Compatibility shim for `from app.main import app` import path.

Khi `uvicorn app.main:app` được gọi, uvicorn expects module `app.main:app`.
File này re-export từ package `app.main` (FastAPI app factory).
"""
