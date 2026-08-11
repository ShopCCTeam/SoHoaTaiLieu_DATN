"""Pydantic schemas for Job Management."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

JobStatus = Literal["QUEUED", "PROCESSING", "SUCCEEDED", "FAILED", "CANCELLED"]


class JobResponse(BaseModel):
    id: str
    type: str
    status: JobStatus
    progress: int = 0
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobResponseEnvelope(BaseModel):
    success: Literal[True] = True
    data: JobResponse
