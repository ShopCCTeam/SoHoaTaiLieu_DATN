"""Unit tests for direct single-image OCR support."""

from __future__ import annotations

import pytest

from app.services.ocr_engine import (
    OcrBlockResult,
    OcrEngineService,
    OcrEngineStrategy,
    OcrPageResult,
    _load_image_as_png,
)

VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\x0dIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class ImageSpyStrategy(OcrEngineStrategy):
    """Minimal strategy proving the service uses the direct-image interface."""

    def __init__(self) -> None:
        self.image_calls = 0

    def process_pdf(self, pdf_bytes: bytes) -> list[OcrPageResult]:
        raise AssertionError("PDF route must not be called for a source image")

    def process_image(self, image_bytes: bytes) -> list[OcrPageResult]:
        self.image_calls += 1
        assert image_bytes == VALID_PNG_BYTES
        return [
            OcrPageResult(
                page_number=1,
                width=1,
                height=1,
                rendered_image_bytes=VALID_PNG_BYTES,
                blocks=[
                    OcrBlockResult(
                        page_number=1,
                        block_index=0,
                        text_content="Ảnh kiểm thử",
                        confidence=0.99,
                        bbox=[0.0, 0.0, 1.0, 1.0],
                    )
                ],
            )
        ]


def test_process_image_uses_direct_image_strategy() -> None:
    primary = ImageSpyStrategy()
    service = OcrEngineService(primary_engine=primary, fallback_engine=ImageSpyStrategy())

    pages = service.process_image(VALID_PNG_BYTES)

    assert primary.image_calls == 1
    assert pages[0].page_number == 1
    assert pages[0].block_count == 1
    assert pages[0].rendered_image_bytes == VALID_PNG_BYTES


def test_load_image_as_png_preserves_source_dimensions_for_review() -> None:
    pytest.importorskip("PIL", reason="Chuẩn hoá ảnh cần extra OCR (Pillow).")
    image, width, height, review_png = _load_image_as_png(VALID_PNG_BYTES)

    assert image.mode == "RGB"
    assert (width, height) == (1, 1)
    assert review_png.startswith(b"\x89PNG\r\n\x1a\n")
