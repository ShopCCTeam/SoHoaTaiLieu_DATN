"""Unit tests for PDF Security Validator service."""

from __future__ import annotations

from io import BytesIO

import pytest
from fastapi import UploadFile

from app.core.errors import ApiError, ErrorCode
from app.services.pdf_validator import (
    validate_pdf_bytes,
    validate_upload_file,
)

VALID_PDF_BYTES = (
    b"%PDF-1.7 header\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
)


def test_validate_pdf_bytes_success() -> None:
    checksum, total_bytes = validate_pdf_bytes(VALID_PDF_BYTES, content_type="application/pdf")
    assert len(checksum) == 64
    assert total_bytes == len(VALID_PDF_BYTES)


def test_validate_pdf_bytes_invalid_mime() -> None:
    with pytest.raises(ApiError) as exc_info:
        validate_pdf_bytes(VALID_PDF_BYTES, content_type="text/plain")
    assert exc_info.value.status_code == 415
    assert exc_info.value.code == ErrorCode.INVALID_FILE_TYPE


def test_validate_pdf_bytes_invalid_magic_bytes() -> None:
    invalid_bytes = b"NOT_A_PDF_FILE_HEADER"
    with pytest.raises(ApiError) as exc_info:
        validate_pdf_bytes(invalid_bytes, content_type="application/pdf")
    assert exc_info.value.status_code == 415
    assert exc_info.value.code == ErrorCode.INVALID_FILE_TYPE


def test_validate_pdf_bytes_file_too_large() -> None:
    large_bytes = b"%PDF-" + b"0" * (50 * 1024 * 1024 + 1)
    with pytest.raises(ApiError) as exc_info:
        validate_pdf_bytes(large_bytes, content_type="application/pdf")
    assert exc_info.value.status_code == 413
    assert exc_info.value.code == ErrorCode.FILE_SIZE_EXCEEDED


@pytest.mark.asyncio
async def test_validate_upload_file_stream_success() -> None:
    upload_file = UploadFile(
        filename="test.pdf",
        file=BytesIO(VALID_PDF_BYTES),
        headers={"content-type": "application/pdf"},
    )
    full_bytes, checksum, total_bytes, detected_format = await validate_upload_file(upload_file)
    assert full_bytes == VALID_PDF_BYTES
    assert len(checksum) == 64
    assert total_bytes == len(VALID_PDF_BYTES)
    assert detected_format == "pdf"
