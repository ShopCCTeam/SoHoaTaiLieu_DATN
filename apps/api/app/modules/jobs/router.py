"""FastAPI Router for Job Management endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.core.errors import conflict, forbidden, not_found
from app.db.session import get_session
from app.models.job import Job
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.modules.jobs.schemas import JobResponse, JobResponseEnvelope

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{id}", response_model=JobResponseEnvelope)
async def get_job_status(
    id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobResponseEnvelope:
    """Get status of an async background job (Polling endpoint)."""
    request_id = getattr(request.state, "request_id", "")
    stmt = select(Job).where(Job.id == id)
    res = await session.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise not_found(detail=f"Tiến trình với ID '{id}' không tồn tại.", request_id=request_id)

    # Allow owner or admin/staff
    is_staff_or_admin = current_user.role in (UserRole.ADMIN.value, UserRole.STAFF.value)
    if not is_staff_or_admin and job.created_by != current_user.id:
        raise forbidden(detail="Bạn không có quyền xem tiến trình này.", request_id=request_id)

    return JobResponseEnvelope(data=JobResponse.model_validate(job))


@router.post("/{id}/cancel", response_model=JobResponseEnvelope)
async def cancel_job(
    id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobResponseEnvelope:
    """Cancel a running or queued job."""
    request_id = getattr(request.state, "request_id", "")
    stmt = select(Job).where(Job.id == id)
    res = await session.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise not_found(detail=f"Tiến trình với ID '{id}' không tồn tại.", request_id=request_id)

    if current_user.role != UserRole.ADMIN.value and job.created_by != current_user.id:
        raise forbidden(detail="Bạn không có quyền huỷ tiến trình này.", request_id=request_id)

    if job.status in ("SUCCEEDED", "FAILED", "CANCELLED"):
        raise conflict(
            detail=f"Tiến trình đã ở trạng thái '{job.status}' nên không thể huỷ.",
            request_id=request_id,
        )

    job.status = "CANCELLED"
    job.finished_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(job)

    return JobResponseEnvelope(data=JobResponse.model_validate(job))
