"""OCR strategies for scanned and text-layer PDFs.

Render scanned pages with PyMuPDF at the configured DPI. If a page already has
at least the configured amount of selectable text, preserve that text directly
instead of running OCR. This keeps the inference and fine-tuning render standard
aligned at 300 DPI by default.
"""

from __future__ import annotations

import io
import time
from abc import ABC, abstractmethod
from base64 import b64decode
from dataclasses import dataclass, field
from typing import Any

from structlog import get_logger

from app.core.config import get_settings
from app.core.enums import OCRPageStatus, OCRReviewStatus
from app.services.ocr_preprocessing import OcrPreprocessOptions, preprocess_ocr_image

logger = get_logger(__name__)

OCR_CONFIDENCE_THRESHOLD: float = 0.9
OCR_RENDER_DPI: int = 300
OCR_TEXT_LAYER_MIN_CHARACTERS: int = 50
TEST_PAGE_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9JHvsAAAAASUVORK5CYII="
)


@dataclass
class OcrBlockResult:
    page_number: int
    block_index: int
    text_content: str
    confidence: float
    bbox: list[float]
    requires_review: bool = False
    review_status: str = OCRReviewStatus.APPROVED.value
    processing_time_ms: int = 100


@dataclass
class OcrPageResult:
    page_number: int
    width: int | None = 612
    height: int | None = 792
    image_key: str | None = None
    rendered_image_bytes: bytes | None = field(default=None, repr=False)
    status: str = OCRPageStatus.COMPLETED.value
    block_count: int = 0
    has_warnings: bool = False
    blocks: list[OcrBlockResult] = field(default_factory=list)


def has_usable_text_layer(text: str, min_characters: int) -> bool:
    """Return whether a PDF page contains enough selectable text to skip OCR."""
    normalized = "".join(text.split())
    return len(normalized) >= min_characters


def build_text_layer_page(
    *,
    page_number: int,
    text: str,
    width: int,
    height: int,
) -> OcrPageResult:
    """Represent selectable PDF text as one full-page, high-confidence block."""
    return OcrPageResult(
        page_number=page_number,
        width=width,
        height=height,
        blocks=[
            OcrBlockResult(
                page_number=page_number,
                block_index=0,
                text_content=text.strip(),
                confidence=1.0,
                bbox=[0.0, 0.0, float(width), float(height)],
                processing_time_ms=0,
            )
        ],
    )


class OcrEngineStrategy(ABC):
    """Strategy interface for OCR engines."""

    @abstractmethod
    def process_pdf(self, pdf_bytes: bytes) -> list[OcrPageResult]:
        """Extract page text blocks from a PDF byte stream."""

    def process_image(self, image_bytes: bytes) -> list[OcrPageResult]:
        """Default image path for simple test strategies; production engines override it."""
        return self.process_pdf(image_bytes)


def _load_image_as_png(image_bytes: bytes) -> tuple[Any, int, int, bytes]:
    """Decode one source image and create its non-public PNG review rendition."""
    try:
        from PIL import Image
    except ImportError as err:
        msg = "Pillow is required to decode uploaded JPEG/PNG documents"
        raise RuntimeError(msg) from err

    try:
        with Image.open(io.BytesIO(image_bytes)) as source_image:
            source_image.load()
            normalized_image = source_image.convert("RGB")
        width, height = normalized_image.size
        output = io.BytesIO()
        normalized_image.save(output, format="PNG")
        return normalized_image, width, height, output.getvalue()
    except Exception as exc:
        raise RuntimeError(f"Uploaded image could not be decoded: {exc}") from exc


class _PdfPageRenderer:
    """Shared PyMuPDF utilities for native OCR strategies."""

    def __init__(self, render_dpi: int, text_layer_min_characters: int) -> None:
        self.render_dpi = render_dpi
        self.text_layer_min_characters = text_layer_min_characters

    def _load_fitz(self) -> Any:
        try:
            import fitz
        except ImportError as err:
            msg = "PyMuPDF (fitz) is not installed — required to render PDF pages"
            raise RuntimeError(msg) from err
        return fitz

    def _text_layer_page(
        self,
        page: Any,
        page_number: int,
        pix: Any,
    ) -> OcrPageResult | None:
        text = page.get_text("text")
        if not has_usable_text_layer(text, self.text_layer_min_characters):
            return None

        result = build_text_layer_page(
            page_number=page_number,
            text=text,
            width=int(pix.width),
            height=int(pix.height),
        )
        result.rendered_image_bytes = pix.tobytes("png")
        return result

    def _render_page(self, page: Any) -> Any:
        """Render an RGB page at the shared OCR/training DPI."""
        fitz = self._load_fitz()
        return page.get_pixmap(
            dpi=self.render_dpi,
            colorspace=fitz.csRGB,
            alpha=False,
        )


class PaddleOcrStrategy(_PdfPageRenderer, OcrEngineStrategy):
    """Primary OCR engine using PaddleOCR on rendered scanned pages."""

    def __init__(
        self,
        render_dpi: int = OCR_RENDER_DPI,
        text_layer_min_characters: int = OCR_TEXT_LAYER_MIN_CHARACTERS,
        preprocess_options: OcrPreprocessOptions | None = None,
    ) -> None:
        super().__init__(render_dpi, text_layer_min_characters)
        self.preprocess_options = preprocess_options or OcrPreprocessOptions()

    def process_pdf(self, pdf_bytes: bytes) -> list[OcrPageResult]:
        try:
            from paddleocr import PaddleOCR  # type: ignore[import-not-found]
        except ImportError as err:
            msg = "PaddleOCR module is not installed in the current environment"
            raise RuntimeError(msg) from err

        try:
            import numpy as np

            fitz = self._load_fitz()
            ocr = PaddleOCR(use_angle_cls=True, lang="vi", show_log=False)
            pages: list[OcrPageResult] = []

            with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
                for page_number, page in enumerate(document, start=1):
                    pix = self._render_page(page)
                    text_page = self._text_layer_page(page, page_number, pix)
                    if text_page is not None:
                        pages.append(text_page)
                        continue

                    started = time.perf_counter()
                    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                        pix.height, pix.width, pix.n
                    )
                    ocr_image = preprocess_ocr_image(image, self.preprocess_options)
                    results = ocr.ocr(ocr_image, cls=True)
                    blocks = _paddle_blocks(results, page_number, pix.width, pix.height)
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    for block in blocks:
                        block.processing_time_ms = elapsed_ms
                    pages.append(
                        OcrPageResult(
                            page_number=page_number,
                            width=pix.width,
                            height=pix.height,
                            rendered_image_bytes=pix.tobytes("png"),
                            blocks=blocks,
                        )
                    )
            return pages
        except Exception as exc:
            raise RuntimeError(f"PaddleOCR execution failed: {exc}") from exc

    def process_image(self, image_bytes: bytes) -> list[OcrPageResult]:
        """OCR a JPG/PNG directly without a PDF render step."""
        try:
            import numpy as np
            from paddleocr import PaddleOCR

            image, width, height, rendered_image_bytes = _load_image_as_png(image_bytes)
            started = time.perf_counter()
            ocr = PaddleOCR(use_angle_cls=True, lang="vi", show_log=False)
            ocr_image = preprocess_ocr_image(np.asarray(image), self.preprocess_options)
            results = ocr.ocr(ocr_image, cls=True)
            blocks = _paddle_blocks(results, 1, width, height)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            for block in blocks:
                block.processing_time_ms = elapsed_ms
            return [
                OcrPageResult(
                    page_number=1,
                    width=width,
                    height=height,
                    rendered_image_bytes=rendered_image_bytes,
                    blocks=blocks,
                )
            ]
        except Exception as exc:
            raise RuntimeError(f"PaddleOCR image execution failed: {exc}") from exc


class TesseractOcrStrategy(_PdfPageRenderer, OcrEngineStrategy):
    """Fallback OCR engine using Tesseract on rendered scanned pages."""

    def __init__(
        self,
        render_dpi: int = OCR_RENDER_DPI,
        text_layer_min_characters: int = OCR_TEXT_LAYER_MIN_CHARACTERS,
        preprocess_options: OcrPreprocessOptions | None = None,
    ) -> None:
        super().__init__(render_dpi, text_layer_min_characters)
        self.preprocess_options = preprocess_options or OcrPreprocessOptions()

    def process_pdf(self, pdf_bytes: bytes) -> list[OcrPageResult]:
        try:
            import pytesseract  # type: ignore[import-not-found]
            from PIL import Image
        except ImportError as err:
            msg = "Tesseract (pytesseract) and Pillow are required for fallback OCR"
            raise RuntimeError(msg) from err

        try:
            fitz = self._load_fitz()
            pages: list[OcrPageResult] = []

            with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
                for page_number, page in enumerate(document, start=1):
                    pix = self._render_page(page)
                    text_page = self._text_layer_page(page, page_number, pix)
                    if text_page is not None:
                        pages.append(text_page)
                        continue

                    started = time.perf_counter()
                    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    if self.preprocess_options.enabled:
                        import numpy as np

                        processed = preprocess_ocr_image(
                            np.asarray(image),
                            self.preprocess_options,
                        )
                        image = Image.fromarray(processed)
                    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                    blocks = _tesseract_blocks(data, page_number)
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    for block in blocks:
                        block.processing_time_ms = elapsed_ms
                    pages.append(
                        OcrPageResult(
                            page_number=page_number,
                            width=pix.width,
                            height=pix.height,
                            rendered_image_bytes=pix.tobytes("png"),
                            blocks=blocks,
                        )
                    )
            return pages
        except Exception as exc:
            raise RuntimeError(f"Tesseract execution failed: {exc}") from exc

    def process_image(self, image_bytes: bytes) -> list[OcrPageResult]:
        """OCR a JPG/PNG directly without a PDF render step."""
        try:
            import pytesseract

            image, width, height, rendered_image_bytes = _load_image_as_png(image_bytes)
            started = time.perf_counter()
            if self.preprocess_options.enabled:
                import numpy as np
                from PIL import Image

                image = Image.fromarray(
                    preprocess_ocr_image(np.asarray(image), self.preprocess_options)
                )
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            blocks = _tesseract_blocks(data, 1)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            for block in blocks:
                block.processing_time_ms = elapsed_ms
            return [
                OcrPageResult(
                    page_number=1,
                    width=width,
                    height=height,
                    rendered_image_bytes=rendered_image_bytes,
                    blocks=blocks,
                )
            ]
        except Exception as exc:
            raise RuntimeError(f"Tesseract image execution failed: {exc}") from exc


def _paddle_blocks(
    results: list[Any] | None,
    page_number: int,
    width: int,
    height: int,
) -> list[OcrBlockResult]:
    """Convert PaddleOCR's quadrilateral output to rectangular block DTOs."""
    if not results or not results[0]:
        return []

    blocks: list[OcrBlockResult] = []
    for block_index, line in enumerate(results[0]):
        points, (text, confidence) = line
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        blocks.append(
            OcrBlockResult(
                page_number=page_number,
                block_index=block_index,
                text_content=str(text),
                confidence=float(confidence),
                bbox=[
                    max(0.0, float(min(xs))),
                    max(0.0, float(min(ys))),
                    min(float(width), float(max(xs))),
                    min(float(height), float(max(ys))),
                ],
            )
        )
    return blocks


def _tesseract_blocks(data: dict[str, list[Any]], page_number: int) -> list[OcrBlockResult]:
    """Convert Tesseract's tabular result into OCR block DTOs."""
    blocks: list[OcrBlockResult] = []
    for index, raw_text in enumerate(data.get("text", [])):
        text = str(raw_text).strip()
        confidence = float(data["conf"][index])
        if not text or confidence <= 0:
            continue
        x = float(data["left"][index])
        y = float(data["top"][index])
        width = float(data["width"][index])
        height = float(data["height"][index])
        blocks.append(
            OcrBlockResult(
                page_number=page_number,
                block_index=len(blocks),
                text_content=text,
                confidence=confidence / 100.0,
                bbox=[x, y, x + width, y + height],
            )
        )
    return blocks


class FallbackMockOcrStrategy(OcrEngineStrategy):
    """Deterministic test-only strategy; never used without explicit opt-in."""

    def process_pdf(self, pdf_bytes: bytes) -> list[OcrPageResult]:
        suspicious = b"LOW_CONFIDENCE_TEST" in pdf_bytes or b"suspicious" in pdf_bytes
        low_confidence = 0.65 if suspicious else 0.92
        return [
            OcrPageResult(
                page_number=1,
                width=1,
                height=1,
                rendered_image_bytes=TEST_PAGE_PNG,
                blocks=[
                    OcrBlockResult(
                        page_number=1,
                        block_index=0,
                        text_content="CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
                        confidence=0.98,
                        bbox=[54.0, 720.0, 540.0, 745.0],
                    ),
                    OcrBlockResult(
                        page_number=1,
                        block_index=1,
                        text_content="Quyết định số 123/QĐ-CTSV",
                        confidence=low_confidence,
                        bbox=[100.0, 650.0, 500.0, 675.0],
                    ),
                ],
            )
        ]

    def process_image(self, image_bytes: bytes) -> list[OcrPageResult]:
        """Return deterministic page metadata for explicitly injected test OCR only."""
        return self.process_pdf(image_bytes)


class OcrEngineService:
    """Select primary/fallback engines and apply review threshold consistently."""

    def __init__(
        self,
        primary_engine: OcrEngineStrategy | None = None,
        fallback_engine: OcrEngineStrategy | None = None,
        confidence_threshold: float | None = None,
    ) -> None:
        settings = get_settings()
        preprocess_options = OcrPreprocessOptions(
            enabled=settings.ocr_preprocess_enabled,
            deskew=settings.ocr_preprocess_deskew,
            denoise_kernel_size=settings.ocr_preprocess_denoise_kernel_size,
            binarize=settings.ocr_preprocess_binarize,
            adaptive_threshold_block_size=settings.ocr_preprocess_adaptive_threshold_block_size,
            adaptive_threshold_c=settings.ocr_preprocess_adaptive_threshold_c,
        )
        self.primary_engine = primary_engine or PaddleOcrStrategy(
            settings.ocr_render_dpi,
            settings.ocr_text_layer_min_characters,
            preprocess_options,
        )
        self.fallback_engine = fallback_engine or TesseractOcrStrategy(
            settings.ocr_render_dpi,
            settings.ocr_text_layer_min_characters,
            preprocess_options,
        )
        self.mock_engine = FallbackMockOcrStrategy()
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.ocr_default_confidence_threshold
        )

    def process_pdf(self, pdf_bytes: bytes, allow_mock: bool = False) -> list[OcrPageResult]:
        """Run primary then fallback OCR; use mock only when explicitly requested by tests."""
        try:
            pages = self.primary_engine.process_pdf(pdf_bytes)
            logger.info("ocr_processed_with_primary_engine", engine="paddleocr")
        except Exception as primary_err:
            logger.warning("primary_ocr_failed_trying_fallback", error=str(primary_err))
            try:
                pages = self.fallback_engine.process_pdf(pdf_bytes)
                logger.info("ocr_processed_with_fallback_engine", engine="tesseract")
            except Exception as fallback_err:
                if allow_mock:
                    logger.warning(
                        "all_ocr_engines_failed_using_mock_explicit_opt_in",
                        primary=str(primary_err),
                        fallback=str(fallback_err),
                    )
                    pages = self.mock_engine.process_pdf(pdf_bytes)
                else:
                    msg = (
                        "All OCR engines failed. "
                        f"Primary (PaddleOCR): {primary_err}. "
                        f"Fallback (Tesseract): {fallback_err}."
                    )
                    logger.error(
                        "all_ocr_engines_failed",
                        primary=str(primary_err),
                        fallback=str(fallback_err),
                    )
                    raise RuntimeError(msg) from fallback_err

        for page in pages:
            page.has_warnings = False
            for block in page.blocks:
                if block.confidence < self.confidence_threshold:
                    block.requires_review = True
                    block.review_status = OCRReviewStatus.PENDING.value
                    page.has_warnings = True
                else:
                    block.requires_review = False
                    block.review_status = OCRReviewStatus.APPROVED.value
            page.block_count = len(page.blocks)
        return pages

    def process_image(self, image_bytes: bytes, allow_mock: bool = False) -> list[OcrPageResult]:
        """Run primary then fallback OCR directly on a validated JPEG or PNG."""
        try:
            pages = self.primary_engine.process_image(image_bytes)
            logger.info("ocr_image_processed_with_primary_engine", engine="paddleocr")
        except Exception as primary_err:
            logger.warning("primary_image_ocr_failed_trying_fallback", error=str(primary_err))
            try:
                pages = self.fallback_engine.process_image(image_bytes)
                logger.info("ocr_image_processed_with_fallback_engine", engine="tesseract")
            except Exception as fallback_err:
                if allow_mock:
                    logger.warning(
                        "all_image_ocr_engines_failed_using_mock_explicit_opt_in",
                        primary=str(primary_err),
                        fallback=str(fallback_err),
                    )
                    pages = self.mock_engine.process_image(image_bytes)
                else:
                    msg = (
                        "All OCR engines failed. "
                        f"Primary (PaddleOCR): {primary_err}. "
                        f"Fallback (Tesseract): {fallback_err}."
                    )
                    logger.error(
                        "all_image_ocr_engines_failed",
                        primary=str(primary_err),
                        fallback=str(fallback_err),
                    )
                    raise RuntimeError(msg) from fallback_err

        for page in pages:
            page.has_warnings = False
            for block in page.blocks:
                if block.confidence < self.confidence_threshold:
                    block.requires_review = True
                    block.review_status = OCRReviewStatus.PENDING.value
                    page.has_warnings = True
                else:
                    block.requires_review = False
                    block.review_status = OCRReviewStatus.APPROVED.value
            page.block_count = len(page.blocks)
        return pages


__all__ = [
    "OCR_CONFIDENCE_THRESHOLD",
    "OCR_RENDER_DPI",
    "OCR_TEXT_LAYER_MIN_CHARACTERS",
    "FallbackMockOcrStrategy",
    "OcrBlockResult",
    "OcrEngineService",
    "OcrEngineStrategy",
    "OcrPageResult",
    "PaddleOcrStrategy",
    "TesseractOcrStrategy",
    "build_text_layer_page",
    "has_usable_text_layer",
]
