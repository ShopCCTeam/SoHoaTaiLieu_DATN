"""Configurable, opt-in preprocessing for rendered OCR page images."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OcrPreprocessOptions:
    """Controls deterministic image preprocessing before native OCR.

    The stage is disabled by default to preserve the established 300 DPI OCR
    baseline. It can be enabled only after a corpus-specific comparison.
    """

    enabled: bool = False
    deskew: bool = True
    denoise_kernel_size: int = 3
    binarize: bool = True
    adaptive_threshold_block_size: int = 31
    adaptive_threshold_c: int = 11


def preprocess_ocr_image(image: Any, options: OcrPreprocessOptions) -> Any:
    """Apply configured preprocessing to an RGB/gray NumPy image.

    When disabled, this function returns the original image object and imports
    no native OpenCV dependency. This keeps current OCR output deterministic
    during rollout and permits test/CI environments without the OCR extra.
    """
    if not options.enabled:
        return image

    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "OCR preprocessing requires the optional OpenCV and NumPy dependencies."
        ) from exc

    if not isinstance(image, np.ndarray):
        raise TypeError("OCR preprocessing expects a NumPy image array.")
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    elif image.ndim == 2:
        gray = image
    else:
        raise ValueError("OCR preprocessing expects a 2D grayscale or 3D RGB image.")

    processed = gray
    if options.deskew:
        processed = _deskew(processed, cv2, np)

    if options.denoise_kernel_size > 1:
        kernel_size = _odd_kernel(options.denoise_kernel_size)
        processed = cv2.medianBlur(processed, kernel_size)

    if options.binarize:
        block_size = _odd_kernel(max(3, options.adaptive_threshold_block_size))
        processed = cv2.adaptiveThreshold(
            processed,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            options.adaptive_threshold_c,
        )

    return processed


def _deskew(gray: Any, cv2: Any, np: Any) -> Any:
    """Estimate foreground orientation and rotate only when a stable angle exists."""
    foreground = np.column_stack(np.where(gray < 250))
    if len(foreground) < 20:
        return gray

    angle = cv2.minAreaRect(foreground.astype("float32"))[-1]
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90
    if abs(angle) < 0.1:
        return gray

    height, width = gray.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(
        gray,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )


def _odd_kernel(value: int) -> int:
    """Return a positive odd kernel size accepted by OpenCV filters."""
    return value if value % 2 else value + 1


__all__ = ["OcrPreprocessOptions", "preprocess_ocr_image"]
