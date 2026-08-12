"""Validation helpers for document upload security boundaries."""

from __future__ import annotations

import hashlib
from typing import Literal, TypeAlias

from fastapi import UploadFile

from app.core.errors import payload_too_large, unsupported_media_type

MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # PDF: 50 MB
MAX_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024  # JPEG/PNG: 10 MB
PDF_MAGIC_BYTES: bytes = b"%PDF-"
JPEG_MAGIC_BYTES: bytes = b"\xff\xd8\xff"
PNG_MAGIC_BYTES: bytes = b"\x89PNG\r\n\x1a\n"

FileFormat: TypeAlias = Literal["pdf", "jpeg", "png"]
ALLOWED_MIME_TYPE: str = "application/pdf"  # Backward-compatible PDF constant.
ALLOWED_MIME_TYPES: dict[FileFormat, str] = {
    "pdf": "application/pdf",
    "jpeg": "image/jpeg",
    "png": "image/png",
}
FILE_EXTENSION_BY_FORMAT: dict[FileFormat, str] = {
    "pdf": "pdf",
    "jpeg": "jpg",
    "png": "png",
}


def _detect_file_format(file_bytes: bytes) -> FileFormat | None:
    """Identify an accepted upload format only from its magic bytes."""
    if file_bytes.startswith(PDF_MAGIC_BYTES):
        return "pdf"
    if file_bytes.startswith(JPEG_MAGIC_BYTES):
        return "jpeg"
    if file_bytes.startswith(PNG_MAGIC_BYTES):
        return "png"
    return None


def _normalized_content_type(content_type: str) -> str:
    """Drop optional multipart parameters before comparing a MIME type."""
    return content_type.split(";", maxsplit=1)[0].strip().lower()


def _validate_detected_file(
    file_bytes: bytes,
    content_type: str | None,
    request_id: str,
    *,
    require_content_type: bool,
) -> FileFormat:
    """Require an accepted magic-byte signature and its matching MIME type."""
    detected_format = _detect_file_format(file_bytes)
    if detected_format is None:
        raise unsupported_media_type(
            detail="Nội dung file không đúng định dạng PDF, JPEG hoặc PNG được hỗ trợ.",
            request_id=request_id,
        )

    if content_type is None or not content_type.strip():
        if require_content_type:
            raise unsupported_media_type(
                detail="Content-Type phải là application/pdf, image/jpeg hoặc image/png.",
                request_id=request_id,
            )
        return detected_format

    normalized_content_type = _normalized_content_type(content_type)
    expected_content_type = ALLOWED_MIME_TYPES[detected_format]
    if normalized_content_type != expected_content_type:
        raise unsupported_media_type(
            detail=(
                f"Content-Type '{content_type}' không khớp với nội dung "
                f"{detected_format.upper()} đã phát hiện."
            ),
            request_id=request_id,
        )

    return detected_format


def validate_pdf_bytes(
    file_bytes: bytes,
    content_type: str | None = None,
    request_id: str = "",
) -> tuple[str, int]:
    """Validate a raw PDF byte stream while retaining the legacy helper contract."""
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise payload_too_large(
            detail="Dung lượng tệp PDF không được vượt quá 50MB.",
            request_id=request_id,
        )

    detected_format = _validate_detected_file(
        file_bytes,
        content_type,
        request_id,
        require_content_type=False,
    )
    if detected_format != "pdf":
        raise unsupported_media_type(
            detail="Nội dung file không đúng định dạng PDF (thiếu magic bytes '%PDF-').",
            request_id=request_id,
        )

    checksum = hashlib.sha256(file_bytes).hexdigest()
    return checksum, len(file_bytes)


async def validate_upload_file(
    upload_file: UploadFile,
    request_id: str = "",
) -> tuple[bytes, str, int, FileFormat]:
    """Validate a multipart upload and return bytes, checksum, size and detected format."""
    header = await upload_file.read(1024)
    detected_format = _validate_detected_file(
        header,
        upload_file.content_type,
        request_id,
        require_content_type=True,
    )

    max_file_size = (
        MAX_FILE_SIZE_BYTES if detected_format == "pdf" else MAX_IMAGE_SIZE_BYTES
    )
    max_size_detail = "50MB với PDF và 10MB với JPEG/PNG"
    if len(header) > max_file_size:
        raise payload_too_large(
            detail=f"Dung lượng tệp không được vượt quá {max_size_detail}.",
            request_id=request_id,
        )

    hasher = hashlib.sha256(header)
    content_chunks = [header]
    total_bytes = len(header)

    while chunk := await upload_file.read(64 * 1024):
        total_bytes += len(chunk)
        if total_bytes > max_file_size:
            raise payload_too_large(
                detail=f"Dung lượng tệp không được vượt quá {max_size_detail}.",
                request_id=request_id,
            )
        hasher.update(chunk)
        content_chunks.append(chunk)

    await upload_file.seek(0)
    full_bytes = b"".join(content_chunks)
    return full_bytes, hasher.hexdigest(), total_bytes, detected_format
