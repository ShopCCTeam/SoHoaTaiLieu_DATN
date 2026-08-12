"""Public service-layer facade for validated PDF/JPEG/PNG document uploads."""

from __future__ import annotations

from fastapi import UploadFile

from app.modules.documents.security import (
    ALLOWED_MIME_TYPES,
    FILE_EXTENSION_BY_FORMAT,
    JPEG_MAGIC_BYTES,
    MAX_FILE_SIZE_BYTES,
    PDF_MAGIC_BYTES,
    PNG_MAGIC_BYTES,
    FileFormat,
    validate_upload_file,
)


class FileValidatorService:
    """Facade retaining validator constants for service-layer consumers."""

    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_BYTES
    ALLOWED_MIME_TYPES = ALLOWED_MIME_TYPES
    FILE_EXTENSION_BY_FORMAT = FILE_EXTENSION_BY_FORMAT
    PDF_MAGIC_BYTES = PDF_MAGIC_BYTES
    JPEG_MAGIC_BYTES = JPEG_MAGIC_BYTES
    PNG_MAGIC_BYTES = PNG_MAGIC_BYTES

    @classmethod
    async def validate_upload_file(
        cls, upload_file: UploadFile, request_id: str = ""
    ) -> tuple[bytes, str, int, FileFormat]:
        return await validate_upload_file(upload_file, request_id)


__all__ = [
    "ALLOWED_MIME_TYPES",
    "FILE_EXTENSION_BY_FORMAT",
    "JPEG_MAGIC_BYTES",
    "MAX_FILE_SIZE_BYTES",
    "PDF_MAGIC_BYTES",
    "PNG_MAGIC_BYTES",
    "FileFormat",
    "FileValidatorService",
    "validate_upload_file",
]
