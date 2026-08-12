#!/usr/bin/env python3
"""B6 HTTP E2E synthetic document pipeline.

Requires a dedicated test runtime. Credentials and endpoint values are supplied
through environment variables; this script never prints them or document/OCR text.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from minio import Minio
from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.job import Job
from app.models.ocr_block import OCRBlock
from app.models.ocr_page import OCRPage

POLL_INTERVAL_SECONDS = 1.0
POLL_TIMEOUT_SECONDS = 120.0
SYNTHETIC_MARKER = "B6_SYNTHETIC_INTERNAL_POLICY_2026"
SEARCH_QUERY = "verified workflow"


@dataclass(frozen=True)
class E2EResult:
    document_id: str
    version_id: str
    job_id: str
    page_count: int
    block_count: int
    chunk_count: int
    embedding_dimension: int
    citation_count: int


class E2EFailure(RuntimeError):
    """Raised when a required B6 pipeline assertion fails."""


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise E2EFailure(f"Missing required environment variable: {name}")
    return value


def _build_synthetic_pdf() -> bytes:
    """Build one safe text-layer PDF; it contains no student or operational data."""
    import pymupdf

    document = pymupdf.open()
    try:
        page = document.new_page()
        page.insert_text((72, 72), SYNTHETIC_MARKER, fontsize=12)
        page.insert_text(
            (72, 96), "Synthetic policy: staff access requires a verified workflow.", fontsize=12
        )
        page.insert_text(
            (72, 120),
            "This document is generated only for isolated B6 runtime verification.",
            fontsize=12,
        )
        return document.tobytes()
    finally:
        document.close()


async def _login(client: httpx.AsyncClient, email: str, password: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        raise E2EFailure(f"Login failed with HTTP {response.status_code}")
    payload = response.json()
    if not payload.get("success") or not payload.get("data", {}).get("access_token"):
        raise E2EFailure("Login response is missing an access token")
    return {"Authorization": f"Bearer {payload['data']['access_token']}"}


async def _poll_job(
    client: httpx.AsyncClient, headers: dict[str, str], job_id: str
) -> dict[str, Any]:
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    last_status = "UNKNOWN"
    while time.monotonic() < deadline:
        response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        if response.status_code != 200:
            raise E2EFailure(f"Job polling failed with HTTP {response.status_code}")
        job = response.json()["data"]
        last_status = job["status"]
        if last_status in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            return job
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
    raise E2EFailure(
        f"Job {job_id} did not finish within {POLL_TIMEOUT_SECONDS:.0f}s; last={last_status}"
    )


async def _database_metadata(version_id: str, job_id: str) -> tuple[int, int, int]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        page_count = await session.scalar(
            select(func.count()).select_from(OCRPage).where(OCRPage.version_id == version_id)
        )
        block_count = await session.scalar(
            select(func.count()).select_from(OCRBlock).where(OCRBlock.version_id == version_id)
        )
        chunk_count = await session.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.version_id == version_id)
        )
        job = await session.get(Job, job_id)
        if job is None or job.status != "SUCCEEDED":
            raise E2EFailure("Database job state is not SUCCEEDED after polling")
        if not page_count or not block_count or not chunk_count:
            raise E2EFailure("Pipeline did not persist pages, OCR blocks, or chunks")

        dimension = await session.scalar(
            select(func.vector_dims(DocumentChunk.embedding))
            .where(DocumentChunk.version_id == version_id)
            .limit(1)
        )
        if dimension != 1024:
            raise E2EFailure(f"Unexpected embedding dimension: {dimension}")
        return int(page_count), int(block_count), int(chunk_count)


def _assert_minio_objects(document_id: str, version_id: str) -> None:
    settings = get_settings()
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key.get_secret_value(),
        secure=settings.minio_secure,
    )
    raw_key = f"documents/raw/{document_id}/{version_id}.pdf"
    page_key = f"documents/pages/{version_id}/1.png"
    try:
        client.stat_object(settings.minio_bucket, raw_key)
        client.stat_object(settings.minio_bucket, page_key)
    except Exception as exc:
        raise E2EFailure("MinIO test bucket is missing required raw/page objects") from exc


def _remove_minio_objects(document_id: str, version_id: str) -> None:
    settings = get_settings()
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key.get_secret_value(),
        secure=settings.minio_secure,
    )
    for key in (
        f"documents/raw/{document_id}/{version_id}.pdf",
        f"documents/pages/{version_id}/1.png",
    ):
        client.remove_object(settings.minio_bucket, key)


async def _cleanup_document(document_id: str) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        version_ids = list(
            (
                await session.scalars(
                    select(DocumentVersion.id).where(DocumentVersion.document_id == document_id)
                )
            ).all()
        )
        if version_ids:
            await session.execute(delete(OCRBlock).where(OCRBlock.version_id.in_(version_ids)))
            await session.execute(delete(OCRPage).where(OCRPage.version_id.in_(version_ids)))
            await session.execute(
                delete(DocumentChunk).where(DocumentChunk.version_id.in_(version_ids))
            )
            await session.execute(delete(Job).where(Job.target_version_id.in_(version_ids)))
            await session.execute(
                delete(DocumentVersion).where(DocumentVersion.id.in_(version_ids))
            )
        await session.execute(delete(Document).where(Document.id == document_id))
        await session.commit()


async def _run() -> E2EResult:
    api_base_url = _required_env("E2E_API_BASE_URL")
    demo_password = _required_env("E2E_DEMO_PASSWORD")
    run_token = uuid.uuid4().hex
    document_id: str | None = None
    version_id: str | None = None

    async with httpx.AsyncClient(base_url=api_base_url, timeout=30.0) as client:
        staff_headers = await _login(client, "staff@example.edu.vn", demo_password)
        student_headers = await _login(client, "student@example.edu.vn", demo_password)

        upload = await client.post(
            "/api/v1/documents",
            headers={**staff_headers, "Idempotency-Key": str(uuid.uuid4())},
            data={
                "title": f"B6 Synthetic Internal {run_token[:8]}",
                "type": "QUY_DINH",
                "scope": "INTERNAL",
                "tags": "b6,synthetic",
            },
            files={"file": ("b6-synthetic.pdf", _build_synthetic_pdf(), "application/pdf")},
        )
        if upload.status_code != 202:
            raise E2EFailure(f"Upload failed with HTTP {upload.status_code}")
        upload_data = upload.json()["data"]
        document_id = upload_data["document_id"]
        job_id = upload_data["job_id"]

        try:
            job = await _poll_job(client, staff_headers, job_id)
            if job["status"] != "SUCCEEDED":
                raise E2EFailure("Worker completed the job without SUCCEEDED status")

            versions = await client.get(
                f"/api/v1/documents/{document_id}/versions", headers=staff_headers
            )
            if versions.status_code != 200 or not versions.json()["data"]:
                raise E2EFailure("Uploaded document has no readable version")
            version_id = versions.json()["data"][0]["id"]

            ocr = await client.get(
                f"/api/v1/documents/{document_id}/versions/{version_id}/ocr", headers=staff_headers
            )
            if ocr.status_code != 200 or not ocr.json()["data"].get("blocks"):
                raise E2EFailure("OCR detail endpoint has no persisted blocks")

            page_count, block_count, chunk_count = await _database_metadata(version_id, job_id)
            _assert_minio_objects(document_id, version_id)

            search = await client.get(
                "/api/v1/search",
                params={"q": SEARCH_QUERY, "scope": "INTERNAL"},
                headers=staff_headers,
            )
            if search.status_code != 200 or not search.json()["data"].get("items"):
                raise E2EFailure("Staff search did not retrieve indexed synthetic document")

            chat = await client.post(
                "/api/v1/chat/query",
                json={
                    "question": "Which access workflow does the synthetic policy require?",
                    "scope": "INTERNAL",
                },
                headers=staff_headers,
            )
            if chat.status_code != 200:
                raise E2EFailure(f"Staff chat failed with HTTP {chat.status_code}")
            chat_data = chat.json()["data"]
            citations = chat_data.get("citations") or []
            if not chat_data.get("has_sufficient_evidence") or not citations:
                raise E2EFailure("Grounded chat returned no sufficient evidence or citation")
            citation = citations[0]
            required_citation_fields = {
                "document_id",
                "document_version_id",
                "page_number",
                "chunk_id",
                "quote",
                "score",
                "bbox",
            }
            if (
                not required_citation_fields.issubset(citation)
                or citation["document_id"] != document_id
            ):
                raise E2EFailure("Chat citation does not point to the uploaded document")

            unrelated = await client.post(
                "/api/v1/chat/query",
                json={"question": "What is the orbital period of a distant exoplanet?"},
                headers=staff_headers,
            )
            if unrelated.status_code != 200:
                raise E2EFailure(
                    f"Insufficient-evidence chat failed with HTTP {unrelated.status_code}"
                )
            unrelated_data = unrelated.json()["data"]
            if unrelated_data.get("has_sufficient_evidence") or unrelated_data.get("citations"):
                raise E2EFailure("Insufficient-evidence chat produced evidence or citations")

            student_detail = await client.get(
                f"/api/v1/documents/{document_id}", headers=student_headers
            )
            student_search = await client.get(
                "/api/v1/search",
                params={"q": SEARCH_QUERY, "scope": "INTERNAL"},
                headers=student_headers,
            )
            student_chat = await client.post(
                "/api/v1/chat/query",
                json={"question": "Show internal policy", "scope": "INTERNAL"},
                headers=student_headers,
            )
            if {
                student_detail.status_code,
                student_search.status_code,
                student_chat.status_code,
            } != {403}:
                raise E2EFailure("Student was not denied every INTERNAL document access path")

            return E2EResult(
                document_id=document_id,
                version_id=version_id,
                job_id=job_id,
                page_count=page_count,
                block_count=block_count,
                chunk_count=chunk_count,
                embedding_dimension=1024,
                citation_count=len(citations),
            )
        finally:
            if document_id and version_id:
                _remove_minio_objects(document_id, version_id)
                await _cleanup_document(document_id)


def main() -> int:
    try:
        result = asyncio.run(_run())
    except E2EFailure as exc:
        print(f"B6 E2E failed: {exc}", file=sys.stderr)
        return 1
    print(
        "B6 E2E passed: "
        f"pages={result.page_count} blocks={result.block_count} chunks={result.chunk_count} "
        f"embedding_dimension={result.embedding_dimension} citations={result.citation_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
