"""Pydantic schemas for Document Management."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DocumentScopeCode

DocumentType = Literal["QUY_CHE", "QUY_DINH", "THONG_BAO", "QUYET_DINH", "HUONG_DAN", "KHAC"]
DocumentStatus = Literal["DRAFT", "UNDER_REVIEW", "APPROVED", "ARCHIVED"]
OCRStatus = Literal["NOT_STARTED", "QUEUED", "PROCESSING", "SUCCEEDED", "FAILED"]
JobStatus = Literal["QUEUED", "PROCESSING", "SUCCEEDED", "FAILED", "CANCELLED"]


class DocumentResponse(BaseModel):
    id: str
    title: str
    type: str
    status: str
    scope: str
    code_number: str | None = None
    issuing_body: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    latest_version: int
    author_id: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentVersionResponse(BaseModel):
    id: str
    document_id: str
    version_number: int
    status: str
    file_url: str
    file_size: int
    checksum: str
    ocr_status: str
    requires_review: bool = False
    supersedes_version_id: str | None = None
    superseded_by_version_id: str | None = None
    change_summary: str | None = None
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(DocumentResponse):
    versions: list[DocumentVersionResponse] = Field(default_factory=list)


class DocumentUpdateSchema(BaseModel):
    title: str | None = None
    type: DocumentType | None = None
    scope: DocumentScopeCode | None = None
    code_number: str | None = None
    issuing_body: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    tags: list[str] | None = None


class VersionUpdateSchema(BaseModel):
    change_summary: str | None = None


class UploadResponseData(BaseModel):
    document_id: str
    job_id: str
    status: JobStatus


class UploadResponseEnvelope(BaseModel):
    success: Literal[True] = True
    data: UploadResponseData


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


class JobCreatedEnvelope(BaseModel):
    success: Literal[True] = True
    data: dict[str, str]


class DocumentListEnvelope(BaseModel):
    success: Literal[True] = True
    data: list[DocumentResponse]
    total: int
    page: int
    limit: int


class DocumentSingleEnvelope(BaseModel):
    success: Literal[True] = True
    data: DocumentResponse


class DocumentDetailEnvelope(BaseModel):
    success: Literal[True] = True
    data: DocumentDetailResponse


class DocumentVersionListEnvelope(BaseModel):
    success: Literal[True] = True
    data: list[DocumentVersionResponse]


class DocumentVersionSingleEnvelope(BaseModel):
    success: Literal[True] = True
    data: DocumentVersionResponse
