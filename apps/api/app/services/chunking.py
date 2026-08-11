"""ChunkingService for Phase D RAG Vector Engine.

Recursive text splitting from OCRBlock/OCRPage data preserving:
- chunk_index (0-indexed integer)
- page_number (1-indexed integer)
- block_ids (list of OCRBlock IDs)
- text (chunk text content string)
- token_count (word count integer)
- Min-Max Envelope Bounding Box [x0, y0, x1, y1]
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypedDict


class ChunkData(TypedDict):
    chunk_index: int
    page_number: int
    block_ids: list[str]
    text: str
    token_count: int
    bbox: list[float]


class ChunkingService:
    """Service for recursively splitting OCR blocks into search chunks."""

    def __init__(
        self,
        max_chars: int = 500,
        overlap_chars: int = 50,
        min_chars: int = 20,
    ) -> None:
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.min_chars = min_chars

    @staticmethod
    def compute_envelope_bbox(bboxes: Sequence[list[float]] | None) -> list[float]:
        """Compute min-max envelope bounding box [x0, y0, x1, y1] from a sequence of bboxes."""
        if not bboxes:
            return [0.0, 0.0, 0.0, 0.0]

        valid_bboxes: list[tuple[float, float, float, float]] = []
        for b in bboxes:
            if not b:
                continue
            try:
                if len(b) >= 4:
                    x0 = float(b[0])
                    y0 = float(b[1])
                    x1 = float(b[2])
                    y1 = float(b[3])
                    valid_bboxes.append((x0, y0, x1, y1))
            except (TypeError, ValueError, IndexError):
                continue

        if not valid_bboxes:
            return [0.0, 0.0, 0.0, 0.0]

        min_x0 = min(b[0] for b in valid_bboxes)
        min_y0 = min(b[1] for b in valid_bboxes)
        max_x1 = max(b[2] for b in valid_bboxes)
        max_y1 = max(b[3] for b in valid_bboxes)

        return [
            round(min_x0, 2),
            round(min_y0, 2),
            round(max_x1, 2),
            round(max_y1, 2),
        ]

    def chunk_ocr_blocks(self, blocks: Sequence[Any]) -> list[ChunkData]:
        """Chunk sequence of OCRBlock ORM objects or dicts into unified chunks."""
        if not blocks:
            return []

        chunks: list[ChunkData] = []
        chunk_index = 0

        # Standardize block items into dicts
        normalized_blocks: list[dict[str, Any]] = []
        for b in blocks:
            if isinstance(b, dict):
                text_content = str(b.get("text_content") or b.get("text") or "").strip()
                normalized_blocks.append(
                    {
                        "id": str(b.get("id", "")),
                        "page_number": int(b.get("page_number", 1)),
                        "text_content": text_content,
                        "bbox": b.get("bbox") or [0.0, 0.0, 0.0, 0.0],
                    }
                )
            else:
                edited = getattr(b, "edited_text", None)
                orig = getattr(b, "text_content", "")
                text_content = str(edited or orig or "").strip()
                normalized_blocks.append(
                    {
                        "id": str(getattr(b, "id", "")),
                        "page_number": int(getattr(b, "page_number", 1)),
                        "text_content": text_content,
                        "bbox": getattr(b, "bbox", [0.0, 0.0, 0.0, 0.0]),
                    }
                )

        # Filter out empty text blocks
        valid_blocks = [b for b in normalized_blocks if b["text_content"]]
        if not valid_blocks:
            return []

        current_block_group: list[dict[str, Any]] = []
        current_text = ""
        current_page = valid_blocks[0]["page_number"]

        def _flush_chunk(group: list[dict[str, Any]]) -> None:
            nonlocal chunk_index, chunks
            if not group:
                return
            full_text = " ".join(b["text_content"] for b in group).strip()
            if not full_text:
                return
            block_ids = [b["id"] for b in group if b["id"]]
            bboxes = [b["bbox"] for b in group]
            page_num = group[0]["page_number"]
            bbox_env = self.compute_envelope_bbox(bboxes)
            tokens = len(full_text.split())

            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "page_number": page_num,
                    "block_ids": block_ids,
                    "text": full_text,
                    "token_count": tokens,
                    "bbox": bbox_env,
                }
            )
            chunk_index += 1

        for blk in valid_blocks:
            text = blk["text_content"]
            blk_page = blk["page_number"]

            # If page changed or text exceeds max_chars
            if current_block_group and (
                blk_page != current_page or len(current_text) + len(text) + 1 > self.max_chars
            ):
                _flush_chunk(current_block_group)

                # Overlap logic
                if self.overlap_chars > 0 and blk_page == current_page and current_block_group:
                    overlap_group: list[dict[str, Any]] = []
                    acc_chars = 0
                    for prev_b in reversed(current_block_group):
                        acc_chars += len(prev_b["text_content"])
                        overlap_group.insert(0, prev_b)
                        if acc_chars >= self.overlap_chars:
                            break
                    current_block_group = overlap_group
                    current_text = " ".join(b["text_content"] for b in current_block_group)
                else:
                    current_block_group = []
                    current_text = ""

            # Handle single block exceeding max_chars
            if len(text) > self.max_chars and not current_block_group:
                sub_texts = self._split_text_recursively(text, self.max_chars)
                for st in sub_texts:
                    chunks.append(
                        {
                            "chunk_index": chunk_index,
                            "page_number": blk_page,
                            "block_ids": [blk["id"]] if blk["id"] else [],
                            "text": st,
                            "token_count": len(st.split()),
                            "bbox": self.compute_envelope_bbox([blk["bbox"]]),
                        }
                    )
                    chunk_index += 1
                current_page = blk_page
                continue

            current_block_group.append(blk)
            current_page = blk_page
            current_text = f"{current_text} {text}".strip() if current_text else text

        if current_block_group:
            _flush_chunk(current_block_group)

        return chunks

    def _split_text_recursively(self, text: str, max_chars: int) -> list[str]:
        """Split long text recursively into segments <= max_chars."""
        if len(text) <= max_chars:
            return [text]

        delimiters = ["\n\n", "\n", ". ", "; ", ", ", " "]
        for delim in delimiters:
            if delim in text:
                parts = text.split(delim)
                sub_chunks: list[str] = []
                curr = ""
                for p in parts:
                    candidate = f"{curr}{delim}{p}" if curr else p
                    if len(candidate) <= max_chars:
                        curr = candidate
                    else:
                        if curr:
                            sub_chunks.append(curr)
                        curr = p
                if curr:
                    sub_chunks.append(curr)
                if all(len(sc) <= max_chars for sc in sub_chunks):
                    return sub_chunks

        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]
