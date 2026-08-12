"""Backward-compatible PDF validation facade.

New PDF/JPEG/PNG callers must import :mod:`app.services.file_validator` instead.
"""

from __future__ import annotations

from fastapi import UploadFile

from app.modules.documents.security import (
    ALLOWED_MIME_TYPE,
    MAX_FILE_SIZE_BYTES,
    PDF_MAGIC_BYTES,
    validate_pdf_bytes,
    validate_upload_file,
)


class PdfValidatorService:
    """Legacy PDF-only facade retained for existing callers."""

    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_BYTES
    PDF_MAGIC_BYTES = PDF_MAGIC_BYTES
    ALLOWED_MIME_TYPE = ALLOWED_MIME_TYPE

    @classmethod
    async def validate_upload_file(
        cls, upload_file: UploadFile, request_id: str = ""
    ) -> tuple[str, int]:
        _, checksum, total_bytes, detected_format = await validate_upload_file(
            upload_file, request_id
        )
        if detected_format != "pdf":
            raise ValueError("PdfValidatorService only accepts PDF uploads")
        return checksum, total_bytes


__all__ = [
    "ALLOWED_MIME_TYPE",
    "MAX_FILE_SIZE_BYTES",
    "PDF_MAGIC_BYTES",
    "PdfValidatorService",
    "validate_pdf_bytes",
    "validate_upload_file",
]
