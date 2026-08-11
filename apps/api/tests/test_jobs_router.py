"""Integration tests for Jobs polling & cancellation router endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.job import Job
from app.models.user import User
from tests.conftest import auth_headers_for


@pytest.mark.asyncio
async def test_get_job_status_polling(
    api_client: AsyncClient, staff_user: User, db_session_factory
) -> None:
    async with db_session_factory() as session:
        job = Job(
            id="job_poll_01",
            type="OCR",
            status="PROCESSING",
            progress=45,
            created_by=staff_user.id,
        )
        session.add(job)
        await session.commit()

    headers = auth_headers_for(staff_user)

    # Success polling
    resp = await api_client.get("/api/v1/jobs/job_poll_01", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == "job_poll_01"
    assert data["status"] == "PROCESSING"
    assert data["progress"] == 45

    # Not found
    resp_nf = await api_client.get("/api/v1/jobs/non_existent_job", headers=headers)
    assert resp_nf.status_code == 404
    assert resp_nf.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_cancel_job(api_client: AsyncClient, staff_user: User, db_session_factory) -> None:
    async with db_session_factory() as session:
        job_active = Job(
            id="job_cancel_01",
            type="OCR",
            status="PROCESSING",
            progress=20,
            created_by=staff_user.id,
        )
        job_finished = Job(
            id="job_finished_01",
            type="OCR",
            status="SUCCEEDED",
            progress=100,
            created_by=staff_user.id,
        )
        session.add_all([job_active, job_finished])
        await session.commit()

    headers = auth_headers_for(staff_user)

    # Cancel active job
    resp_cancel = await api_client.post("/api/v1/jobs/job_cancel_01/cancel", headers=headers)
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["data"]["status"] == "CANCELLED"

    # Cancel finished job -> 409 Conflict
    resp_conflict = await api_client.post("/api/v1/jobs/job_finished_01/cancel", headers=headers)
    assert resp_conflict.status_code == 409
    assert resp_conflict.json()["code"] == "CONFLICT"
