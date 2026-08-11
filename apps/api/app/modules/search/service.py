"""Search module service logic for Phase D RAG Engine (RRF Hybrid Search)."""

from __future__ import annotations

import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.modules.search.schemas import SearchResponse, SearchResultItem
from app.services.embedding import EmbeddingService


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 > 0 and norm2 > 0:
        return float(dot / (norm1 * norm2))
    return 0.0


async def search_documents(
    session: AsyncSession,
    query: str,
    allowed_scopes: list[str],
    requested_scope: str | None = None,
    doc_type: str | None = None,
    alpha: float = 0.5,
    top_k: int = 10,
    page: int = 1,
    size: int = 10,
) -> SearchResponse:
    """Perform RRF hybrid search (Vector similarity + Full-text search)
    with RBAC scope filtering.
    """
    query_clean = query.strip()
    if not query_clean:
        return SearchResponse(items=[], total=0, page=page, size=size, query=query)

    # Generate query vector
    embedding_service = EmbeddingService()
    query_vector = await embedding_service.embed_query(query_clean)

    # Determine DB dialect
    bind = session.bind
    is_postgres = bind is not None and "postgresql" in str(bind.dialect.name)

    # Common document filters
    base_stmt = (
        select(DocumentChunk, Document, DocumentVersion)
        .join(Document, DocumentChunk.document_id == Document.id)
        .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
        .where(Document.deleted_at.is_(None))
        .where(Document.scope.in_(allowed_scopes))
    )

    if requested_scope:
        base_stmt = base_stmt.where(Document.scope == requested_scope)

    if doc_type:
        base_stmt = base_stmt.where(Document.type == doc_type)

    # 1. Vector Search Candidates (Top 50)
    vector_candidates: list[tuple[DocumentChunk, Document, float]] = []
    if is_postgres:
        pg_vec_stmt = base_stmt.order_by(
            DocumentChunk.embedding.cosine_distance(query_vector)
        ).limit(50)
        res_vec = await session.execute(pg_vec_stmt)
        rows_vec = res_vec.all()
        for chunk, doc, _ver in rows_vec:
            # Approx similarity = 1 - cosine_distance
            dist = getattr(chunk, "cosine_distance", 0.0)
            sim = 1.0 - float(dist) if dist else 0.8
            vector_candidates.append((chunk, doc, sim))
    else:
        # SQLite fallback: calculate similarity in python
        res_all = await session.execute(base_stmt.limit(200))
        rows_all = res_all.all()
        scored_chunks: list[tuple[DocumentChunk, Document, float]] = []
        for chunk, doc, _ver in rows_all:
            emb = chunk.embedding
            if isinstance(emb, list):
                sim = _cosine_similarity(query_vector, emb)
                scored_chunks.append((chunk, doc, sim))
        scored_chunks.sort(key=lambda x: x[2], reverse=True)
        vector_candidates = scored_chunks[:50]

    # 2. Full-Text Search Candidates (Top 50)
    fulltext_candidates: list[tuple[DocumentChunk, Document, float]] = []
    if is_postgres:
        from sqlalchemy import func

        pg_ft_stmt = (
            base_stmt.where(
                DocumentChunk.fulltext_tsv.op("@@")(func.plainto_tsquery("simple", query_clean))
            )
            .order_by(
                func.ts_rank(
                    DocumentChunk.fulltext_tsv,
                    func.plainto_tsquery("simple", query_clean),
                ).desc()
            )
            .limit(50)
        )
        res_ft = await session.execute(pg_ft_stmt)
        for chunk, doc, _ver in res_ft.all():
            fulltext_candidates.append((chunk, doc, 1.0))
    else:
        # SQLite fallback: keyword match / ILIKE
        res_ft = await session.execute(base_stmt)
        for chunk, doc, _ver in res_ft.all():
            text_lower = chunk.text.lower()
            q_terms = [t.lower() for t in query_clean.split() if t.strip()]
            matches = sum(1 for t in q_terms if t in text_lower)
            if matches > 0:
                ft_score = float(matches) / max(len(q_terms), 1)
                fulltext_candidates.append((chunk, doc, ft_score))
        fulltext_candidates.sort(key=lambda x: x[2], reverse=True)
        fulltext_candidates = fulltext_candidates[:50]

    # 3. Reciprocal Rank Fusion (RRF)
    k_const = 60
    vector_ranks: dict[str, int] = {
        chunk.id: idx + 1 for idx, (chunk, _, _) in enumerate(vector_candidates)
    }
    vector_scores: dict[str, float] = {chunk.id: score for chunk, _, score in vector_candidates}

    fulltext_ranks: dict[str, int] = {
        chunk.id: idx + 1 for idx, (chunk, _, _) in enumerate(fulltext_candidates)
    }
    fulltext_scores: dict[str, float] = {chunk.id: score for chunk, _, score in fulltext_candidates}

    chunk_map: dict[str, tuple[DocumentChunk, Document]] = {}
    for chunk, doc, _ in vector_candidates:
        chunk_map[chunk.id] = (chunk, doc)
    for chunk, doc, _ in fulltext_candidates:
        chunk_map[chunk.id] = (chunk, doc)

    all_chunk_ids = list(chunk_map.keys())

    fused_results: list[tuple[DocumentChunk, Document, float, float | None, float | None]] = []
    for cid in all_chunk_ids:
        chunk, doc = chunk_map[cid]
        r_v = vector_ranks.get(cid)
        r_f = fulltext_ranks.get(cid)

        rrf_v = (1.0 / (k_const + r_v)) if r_v is not None else 0.0
        rrf_f = (1.0 / (k_const + r_f)) if r_f is not None else 0.0

        rrf_score = alpha * rrf_v + (1.0 - alpha) * rrf_f
        v_score = vector_scores.get(cid)
        f_score = fulltext_scores.get(cid)

        fused_results.append((chunk, doc, rrf_score, v_score, f_score))

    # Sort candidates by combined RRF score descending
    fused_results.sort(key=lambda x: x[2], reverse=True)

    total_count = len(fused_results)

    # Slice for pagination & top_k
    start_idx = (page - 1) * size
    end_idx = min(start_idx + size, top_k)
    paged_items = fused_results[start_idx:end_idx] if start_idx < top_k else []

    items: list[SearchResultItem] = []
    for chunk, doc, score, v_score, f_score in paged_items:
        items.append(
            SearchResultItem(
                chunk_id=chunk.id,
                document_id=doc.id,
                version_id=chunk.version_id,
                document_title=doc.title,
                document_scope=doc.scope,
                document_type=doc.type,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                bbox=chunk.bbox if isinstance(chunk.bbox, list) else [0.0, 0.0, 0.0, 0.0],
                score=round(score, 6),
                vector_score=round(v_score, 4) if v_score is not None else None,
                fulltext_score=round(f_score, 4) if f_score is not None else None,
            )
        )

    return SearchResponse(
        items=items,
        total=total_count,
        page=page,
        size=size,
        query=query_clean,
    )
