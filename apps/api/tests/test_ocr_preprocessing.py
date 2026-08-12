"""Unit tests for optional OCR image preprocessing."""

from __future__ import annotations

from app.services.ocr_preprocessing import OcrPreprocessOptions, preprocess_ocr_image


def test_preprocess_options_default_to_disabled() -> None:
    """Rollout is opt-in so existing OCR output is unchanged until enabled."""
    options = OcrPreprocessOptions()

    assert options.enabled is False
    assert options.deskew is True
    assert options.denoise_kernel_size == 3
    assert options.binarize is True


def test_disabled_preprocessing_returns_original_image_without_cv_dependencies() -> None:
    """Disabled preprocessing must be a no-op and must not import OpenCV."""
    original_image = object()

    processed_image = preprocess_ocr_image(
        original_image,
        OcrPreprocessOptions(enabled=False),
    )

    assert processed_image is original_image
