"""Unit tests for ChunkingService."""

from __future__ import annotations

from app.services.chunking import ChunkingService


def test_compute_envelope_bbox() -> None:
    bboxes = [
        [10.0, 20.0, 100.0, 50.0],
        [5.0, 30.0, 120.0, 90.0],
        [15.0, 10.0, 80.0, 40.0],
    ]
    envelope = ChunkingService.compute_envelope_bbox(bboxes)
    assert envelope == [5.0, 10.0, 120.0, 90.0]


def test_compute_envelope_bbox_empty() -> None:
    assert ChunkingService.compute_envelope_bbox([]) == [0.0, 0.0, 0.0, 0.0]


def test_chunk_ocr_blocks_basic() -> None:
    service = ChunkingService(max_chars=200, overlap_chars=20)
    blocks = [
        {
            "id": "blk_01",
            "page_number": 1,
            "text_content": "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
            "bbox": [10.0, 10.0, 200.0, 30.0],
        },
        {
            "id": "blk_02",
            "page_number": 1,
            "text_content": "Độc lập - Tự do - Hạnh phúc",
            "bbox": [15.0, 35.0, 180.0, 50.0],
        },
    ]

    chunks = service.chunk_ocr_blocks(blocks)
    assert len(chunks) == 1
    c = chunks[0]
    assert c["chunk_index"] == 0
    assert c["page_number"] == 1
    assert c["block_ids"] == ["blk_01", "blk_02"]
    assert "CỘNG HÒA" in c["text"]
    assert "Độc lập" in c["text"]
    assert c["token_count"] == len(c["text"].split())
    assert c["bbox"] == [10.0, 10.0, 200.0, 50.0]


def test_chunk_ocr_blocks_multipage() -> None:
    service = ChunkingService(max_chars=100)
    blocks = [
        {
            "id": "b1",
            "page_number": 1,
            "text_content": "Trang một có nội dung quy chế đào tạo đại học.",
            "bbox": [0.0, 0.0, 100.0, 100.0],
        },
        {
            "id": "b2",
            "page_number": 2,
            "text_content": "Trang hai có nội dung quy định học bổng sinh viên.",
            "bbox": [10.0, 10.0, 110.0, 110.0],
        },
    ]

    chunks = service.chunk_ocr_blocks(blocks)
    assert len(chunks) == 2
    assert chunks[0]["page_number"] == 1
    assert chunks[0]["block_ids"] == ["b1"]
    assert chunks[1]["page_number"] == 2
    assert chunks[1]["block_ids"] == ["b2"]
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["chunk_index"] == 1


def test_chunk_ocr_blocks_single_large_block() -> None:
    service = ChunkingService(max_chars=50)
    long_text = (
        "Quy chế này quy định về đào tạo đại học chính quy bao gồm tổ chức đào tạo, "
        "đánh giá học phần, xét và công nhận tốt nghiệp."
    )
    blocks = [
        {
            "id": "b_large",
            "page_number": 1,
            "text_content": long_text,
            "bbox": [5.0, 5.0, 500.0, 500.0],
        }
    ]

    chunks = service.chunk_ocr_blocks(blocks)
    assert len(chunks) > 1
    for c in chunks:
        assert c["page_number"] == 1
        assert c["block_ids"] == ["b_large"]
        assert len(c["text"]) <= 80


def test_chunk_ocr_blocks_empty() -> None:
    service = ChunkingService()
    assert service.chunk_ocr_blocks([]) == []
    assert service.chunk_ocr_blocks([{"text_content": "   "}]) == []
