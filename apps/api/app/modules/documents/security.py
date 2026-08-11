"""PDF Security & Validation module (Magic Bytes, File Size, Content-Type, SHA-256)."""

from __future__ import annotations

import hashlib

from fastapi import UploadFile

from app.core.errors import payload_too_large, unsupported_media_type

MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
PDF_MAGIC_BYTES: bytes = b"%PDF-"
ALLOWED_MIME_TYPE: str = "application/pdf"


def validate_pdf_bytes(
    file_bytes: bytes,
    content_type: str | None = None,
    request_id: str = "",
) -> tuple[str, int]:
    """Validate raw bytes of a PDF file.

    Returns:
        tuple[str, int]: (sha256_checksum_hex, total_file_size_bytes)
    """
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise payload_too_large(
            detail="Dung lượng tệp PDF không được vượt quá 50MB.",
            request_id=request_id,
        )

    if content_type and not content_type.lower().startswith(ALLOWED_MIME_TYPE):
        raise unsupported_media_type(
            detail=f"Content-Type '{content_type}' không phải 'application/pdf'.",
            request_id=request_id,
        )

    if not file_bytes.startswith(PDF_MAGIC_BYTES):
        raise unsupported_media_type(
            detail="Nội dung file không đúng định dạng PDF (thiếu magic bytes '%PDF-').",
            request_id=request_id,
        )

    checksum = hashlib.sha256(file_bytes).hexdigest()
    return checksum, len(file_bytes)


async def validate_upload_file(
    upload_file: UploadFile,
    request_id: str = "",
) -> tuple[bytes, str, int]:
    """Validate UploadFile stream from FastAPI multipart request.

    Returns:
        tuple[bytes, str, int]: (file_bytes, sha256_checksum_hex, total_file_size_bytes)
    """
    if upload_file.content_type and not upload_file.content_type.lower().startswith(
        ALLOWED_MIME_TYPE
    ):
        raise unsupported_media_type(
            detail=f"Content-Type '{upload_file.content_type}' không phải 'application/pdf'.",
            request_id=request_id,
        )

    header = await upload_file.read(1024)
    if len(header) < 5 or not header.startswith(PDF_MAGIC_BYTES):
        raise unsupported_media_type(
            detail="Nội dung file không đúng định dạng PDF (thiếu magic bytes '%PDF-').",
            request_id=request_id,
        )

    hasher = hashlib.sha256(header)
    content_chunks = [header]
    total_bytes = len(header)

    while chunk := await upload_file.read(64 * 1024):
        total_bytes += len(chunk)
        if total_bytes > MAX_FILE_SIZE_BYTES:
            raise payload_too_large(
                detail="Dung lượng tệp PDF không được vượt quá 50MB.",
                request_id=request_id,
            )
        hasher.update(chunk)
        content_chunks.append(chunk)

    await upload_file.seek(0)
    full_bytes = b"".join(content_chunks)
    return full_bytes, hasher.hexdigest(), total_bytes
