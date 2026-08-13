"""Synthetic dependency smoke for the dedicated OCR-native CI job."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.ocr_native


def test_should_load_native_ocr_dependencies_for_synthetic_ci_smoke() -> None:
    """Verify optional OCR libraries and Tesseract binary without inference/model downloads."""
    pil = pytest.importorskip("PIL")
    pytesseract = pytest.importorskip("pytesseract")
    paddleocr = pytest.importorskip("paddleocr")
    import numpy as np

    image = pil.Image.new("RGB", (1, 1), "white")

    assert np.asarray(image).shape == (1, 1, 3)
    assert paddleocr.PaddleOCR is not None
    assert str(pytesseract.get_tesseract_version())
