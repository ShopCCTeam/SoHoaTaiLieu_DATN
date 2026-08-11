"""Adversarial stress and invariant tests for Phase D.

Created by Challenger 2 Phase D.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import Response
from sqlalchemy import select

from alembic.script import ScriptDirectory
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.ocr_block import OCRBlock
from app.models.ocr_page import OCRPage
from app.models.user import User
from app.services.chunking import ChunkingService
from app.services.embedding import (
    BGEM3EmbeddingStrategy,
    EmbeddingService,
    MockEmbeddingStrategy,
)
from app.worker.tasks import _async_index_document_chunks, index_document_chunks_task


@pytest.fixture
def script_dir() -> ScriptDirectory:
    """Alembic script directory — read directly from filesystem."""
    here = Path(__file__).parent
    alembic_path = here.parent / "alembic"
    return ScriptDirectory(str(alembic_path))


# ============================================================================
# 1. EmbeddingService & Strategies Stress Tests
# ============================================================================


@pytest.mark.asyncio
async def test_embedding_service_strategy_switching(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify strategy switching between BGE-M3 and Mock based on config/parameter."""
    # Test provider="mock"
    srv_mock = EmbeddingService(provider="mock")
    assert isinstance(srv_mock._strategy, MockEmbeddingStrategy)

    # Test provider="bge-m3"
    srv_bge = EmbeddingService(provider="bge-m3")
    assert isinstance(srv_bge._strategy, BGEM3EmbeddingStrategy)

    # Test passing custom strategy directly
    custom_strat = MockEmbeddingStrategy()
    srv_custom = EmbeddingService(strategy=custom_strat)
    assert srv_custom._strategy is custom_strat

    # Test global settings config fallback
    monkeypatch.setattr(
        "app.services.embedding.get_settings",
        lambda: MagicMock(embedding_provider="bge-m3"),
    )
    srv_config = EmbeddingService()
    assert isinstance(srv_config._strategy, BGEM3EmbeddingStrategy)


@pytest.mark.asyncio
async def test_bge_m3_embedding_strategy_success() -> None:
    """Test BGEM3EmbeddingStrategy returns 1024-dim vector on HTTP 200 success."""
    url = "http://127.0.0.1:59999/embed"
    strategy = BGEM3EmbeddingStrategy(api_url=url, model_name="bge-m3")
    valid_vec = [(i % 100) / 100.0 for i in range(1024)]

    mock_resp = Response(200, json={"embedding": valid_vec})
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        vec = await strategy.embed_query("Quy chế học tập 2026")
        assert len(vec) == 1024
        assert vec == valid_vec


@pytest.mark.asyncio
async def test_bge_m3_embedding_strategy_invalid_dim_fallback() -> None:
    """Test BGEM3EmbeddingStrategy fallback when API returns invalid dimension (512)."""
    url = "http://127.0.0.1:59999/embed"
    strategy = BGEM3EmbeddingStrategy(api_url=url, model_name="bge-m3")
    invalid_vec = [0.1] * 512

    mock_resp = Response(200, json={"embedding": invalid_vec})
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        vec_fallback_dim = await strategy.embed_query("Quy chế học tập 2026")
        assert len(vec_fallback_dim) == 1024
        norm = math.sqrt(sum(x * x for x in vec_fallback_dim))
        assert math.isclose(norm, 1.0, rel_tol=1e-5)


@pytest.mark.asyncio
async def test_bge_m3_embedding_strategy_http_500_fallback() -> None:
    """Test BGEM3EmbeddingStrategy falls back to Mock 1024-dim under HTTP 500 error."""
    url = "http://127.0.0.1:59999/embed"
    strategy = BGEM3EmbeddingStrategy(api_url=url, model_name="bge-m3")

    mock_resp = Response(500, text="Internal Error")
    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
        vec_fallback_500 = await strategy.embed_query("Quy chế học tập 2026")
        assert len(vec_fallback_500) == 1024
        assert math.isclose(math.sqrt(sum(x * x for x in vec_fallback_500)), 1.0, rel_tol=1e-5)


@pytest.mark.asyncio
async def test_embedding_vector_dimension_invariant_1024() -> None:
    """Invariant: Every output vector from EmbeddingService must have length == 1024."""
    for provider in ["mock", "bge-m3"]:
        service = EmbeddingService(provider=provider)

        q_vec = await service.embed_query("Test single query embedding")
        assert len(q_vec) == 1024

        t_vecs = await service.embed_texts(["Nội dung 1", "Nội dung 2", "Nội dung 3"])
        assert len(t_vecs) == 3
        for v in t_vecs:
            assert len(v) == 1024


# ============================================================================
# 2. ChunkingService Bbox Calculation & Aggregation Stress Tests
# ============================================================================


def test_chunking_min_max_envelope_bbox_calculation() -> None:
    """Verify compute_envelope_bbox min-max calculation across single, multiple, and edge cases."""
    # Single block bbox
    single_bbox = [[10.0, 20.0, 100.0, 50.0]]
    assert ChunkingService.compute_envelope_bbox(single_bbox) == [10.0, 20.0, 100.0, 50.0]

    # Multiple valid non-zero blocks
    valid_bboxes = [
        [10.0, 20.0, 100.0, 50.0],
        [5.0, 30.0, 120.0, 90.0],
        [15.0, 10.0, 80.0, 40.0],
    ]
    # min_x0 = 5.0, min_y0 = 10.0, max_x1 = 120.0, max_y1 = 90.0
    assert ChunkingService.compute_envelope_bbox(valid_bboxes) == [5.0, 10.0, 120.0, 90.0]

    # Edge case: Empty list, None input
    assert ChunkingService.compute_envelope_bbox([]) == [0.0, 0.0, 0.0, 0.0]
    assert ChunkingService.compute_envelope_bbox(None) == [0.0, 0.0, 0.0, 0.0]

    # Edge cases: missing/invalid coordinates or items
    invalid_bboxes: list[Any] = [
        [],
        None,
        [1.0, 2.0],
        ["invalid", 2.0, 3.0, 4.0],
        [None, None, None, None],
    ]
    assert ChunkingService.compute_envelope_bbox(invalid_bboxes) == [0.0, 0.0, 0.0, 0.0]


def test_chunking_bbox_aggregation_across_ocr_blocks() -> None:
    """Verify chunking OCR blocks aggregates bounding boxes into correct min-max envelope."""
    service = ChunkingService(max_chars=500)
    blocks = [
        {
            "id": "blk_1",
            "page_number": 1,
            "text_content": "Mẫu đơn xin miễn giảm học phí.",
            "bbox": [10.0, 15.0, 200.0, 35.0],
        },
        {
            "id": "blk_2",
            "page_number": 1,
            "text_content": "Kính gửi Ban Giám hiệu nhà trường.",
            "bbox": [8.0, 40.0, 250.0, 60.0],
        },
        {
            "id": "blk_3",
            "page_number": 1,
            "text_content": "Tôi tên là Nguyễn Văn A, MSSV 20260001.",
            "bbox": [12.0, 65.0, 300.0, 85.0],
        },
    ]

    chunks = service.chunk_ocr_blocks(blocks)
    assert len(chunks) == 1
    c = chunks[0]
    assert c["block_ids"] == ["blk_1", "blk_2", "blk_3"]
    # min_x0=8.0, min_y0=15.0, max_x1=300.0, max_y1=85.0
    assert c["bbox"] == [8.0, 15.0, 300.0, 85.0]


# ============================================================================
# 3. Task Idempotency Stress Tests
# ============================================================================


@pytest.mark.asyncio
async def test_index_document_chunks_task_idempotency(
    db_session_factory: Any, admin_user: User
) -> None:
    """Verify index_document_chunks_task idempotency: re-indexing cleanly overwrites old chunks."""
    version_id = "ver_idempotent_01"
    doc_id = "doc_idempotent_01"

    # Setup Document, DocumentVersion, OCRPage, OCRBlocks
    async with db_session_factory() as session:
        doc = Document(
            id=doc_id,
            title="Đơn đăng ký học phần 2026",
            type="THONG_BAO",
            status="APPROVED",
            scope="PUBLIC",
            author_id=admin_user.id,
        )
        ver = DocumentVersion(
            id=version_id,
            document_id=doc_id,
            version_number=1,
            status="APPROVED",
            file_url="/files/idempotent.pdf",
            file_size=2048,
            checksum="hashidempotent",
            ocr_status="SUCCEEDED",
            created_by=admin_user.id,
        )
        page = OCRPage(
            id="page_idem_01",
            version_id=version_id,
            page_number=1,
            width=600,
            height=800,
            status="COMPLETED",
        )
        b1 = OCRBlock(
            id="blk_idem_01",
            version_id=version_id,
            page_id=page.id,
            page_number=1,
            block_index=0,
            text_content="Quy định về thời gian đăng ký học phần học kỳ 1 năm học 2026-2027.",
            confidence=0.98,
            bbox=[10.0, 10.0, 400.0, 40.0],
        )
        b2 = OCRBlock(
            id="blk_idem_02",
            version_id=version_id,
            page_id=page.id,
            page_number=1,
            block_index=1,
            text_content="Sinh viên thực hiện đăng ký trực tuyến qua cổng thông tin sinh viên.",
            confidence=0.96,
            bbox=[10.0, 45.0, 420.0, 75.0],
        )
        session.add_all([doc, ver, page, b1, b2])
        await session.commit()

    # First run of chunk indexing
    res1 = await _async_index_document_chunks(version_id)
    assert res1["status"] == "SUCCEEDED"
    initial_count = res1["chunk_count"]
    assert initial_count > 0

    async with db_session_factory() as session:
        chunks_run1 = (
            (
                await session.execute(
                    select(DocumentChunk).where(DocumentChunk.version_id == version_id)
                )
            )
            .scalars()
            .all()
        )
        assert len(chunks_run1) == initial_count
        run1_ids = {c.id for c in chunks_run1}

    # Second run of chunk indexing (Re-indexing test)
    res2 = await _async_index_document_chunks(version_id)
    assert res2["status"] == "SUCCEEDED"

    async with db_session_factory() as session:
        chunks_run2 = (
            (
                await session.execute(
                    select(DocumentChunk).where(DocumentChunk.version_id == version_id)
                )
            )
            .scalars()
            .all()
        )
        # Count MUST remain initial_count (old chunks deleted, not duplicated!)
        assert len(chunks_run2) == initial_count
        run2_ids = {c.id for c in chunks_run2}
        # Run 2 IDs must be fresh (old IDs deleted and replaced)
        assert run1_ids.isdisjoint(run2_ids)

    # Third run via Celery sync wrapper task
    res3 = index_document_chunks_task(version_id)
    assert res3["status"] == "SUCCEEDED"

    async with db_session_factory() as session:
        chunks_run3 = (
            (
                await session.execute(
                    select(DocumentChunk).where(DocumentChunk.version_id == version_id)
                )
            )
            .scalars()
            .all()
        )
        assert len(chunks_run3) == initial_count


# ============================================================================
# 4. Alembic Migration 0005 Invariants & Upgrade/Downgrade Tests
# ============================================================================


def test_alembic_0005_migration_revision_chain(script_dir: ScriptDirectory) -> None:
    """Verify revision 0005 exists, down_revision is 0004, and head is 0005."""
    revisions = {r.revision: r for r in script_dir.walk_revisions()}
    assert "0005" in revisions
    assert revisions["0005"].down_revision == "0004"
    assert script_dir.get_current_head() in ("0005", "0006")


def test_alembic_0005_upgrade_downgrade_script_execution() -> None:
    """Test Alembic migration 0005 upgrade() and downgrade() functions with a mock bind."""
    mig_path = (
        Path(__file__).parent.parent / "alembic" / "versions" / "0005_document_chunks_pgvector.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0005", mig_path)
    assert spec is not None and spec.loader is not None
    mig_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig_mod)

    # Test upgrade on non-postgres dialect (e.g. sqlite fallback mode)
    mock_bind = MagicMock()
    mock_bind.dialect.name = "sqlite"

    with (
        patch("alembic.op.get_bind", return_value=mock_bind),
        patch("alembic.op.create_table") as mock_create_table,
        patch("alembic.op.create_index") as mock_create_index,
        patch("alembic.op.drop_index") as mock_drop_index,
        patch("alembic.op.drop_table") as mock_drop_table,
    ):
        # Execute upgrade
        mig_mod.upgrade()
        assert mock_create_table.called
        assert mock_create_table.call_args[0][0] == "document_chunks"
        assert mock_create_index.call_count >= 5

        # Execute downgrade
        mig_mod.downgrade()
        assert mock_drop_table.called
        assert mock_drop_table.call_args[0][0] == "document_chunks"
        assert mock_drop_index.call_count >= 5
