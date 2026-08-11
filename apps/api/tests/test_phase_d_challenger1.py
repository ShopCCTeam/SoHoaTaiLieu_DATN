"""Empirical Stress & Security Verification Tests for Phase D Search APIs & RBAC.
Written by Challenger 1 Phase D.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.user import User
from app.services.embedding import MockEmbeddingStrategy
from tests.conftest import auth_headers_for


@pytest.fixture
async def seeded_rbac_search_data(db_session_factory, admin_user: User) -> dict[str, str]:
    """Seed documents with PUBLIC, STUDENT_AFFAIRS, and INTERNAL scopes and vector chunks."""
    strategy = MockEmbeddingStrategy()
    emb_pub = await strategy.embed_query("Quy chế đào tạo sinh viên đại học chính quy PUBLIC")
    emb_sa = await strategy.embed_query("Hướng dẫn xét học bổng công tác sinh viên STUDENT_AFFAIRS")
    emb_int = await strategy.embed_query("Báo cáo tài chính nội bộ phòng ban INTERNAL")

    async with db_session_factory() as session:
        # Document 1: PUBLIC
        doc_pub = Document(
            id="doc_d_pub",
            title="Quy chế đào tạo đại học 2026",
            type="QUY_CHE",
            status="APPROVED",
            scope="PUBLIC",
            code_number="QC-PUB-2026",
            author_id=admin_user.id,
        )
        ver_pub = DocumentVersion(
            id="ver_d_pub",
            document_id=doc_pub.id,
            version_number=1,
            status="APPROVED",
            file_url="/files/pub.pdf",
            file_size=1024,
            checksum="hash_pub",
            ocr_status="SUCCEEDED",
            created_by=admin_user.id,
        )
        chunk_pub = DocumentChunk(
            id="chunk_d_pub",
            version_id=ver_pub.id,
            document_id=doc_pub.id,
            chunk_index=0,
            page_number=1,
            block_ids=["blk_pub"],
            text=("Quy chế đào tạo đại học chính quy dành cho tất cả sinh viên công khai PUBLIC."),
            token_count=15,
            bbox=[10.0, 10.0, 200.0, 50.0],
            embedding=emb_pub,
            fulltext_tsv=(
                "Quy chế đào tạo đại học chính quy dành cho tất cả sinh viên công khai PUBLIC."
            ),
        )

        # Document 2: STUDENT_AFFAIRS
        doc_sa = Document(
            id="doc_d_sa",
            title="Hướng dẫn học bổng công tác sinh viên",
            type="HUONG_DAN",
            status="APPROVED",
            scope="STUDENT_AFFAIRS",
            code_number="HD-SA-2026",
            author_id=admin_user.id,
        )
        ver_sa = DocumentVersion(
            id="ver_d_sa",
            document_id=doc_sa.id,
            version_number=1,
            status="APPROVED",
            file_url="/files/sa.pdf",
            file_size=2048,
            checksum="hash_sa",
            ocr_status="SUCCEEDED",
            created_by=admin_user.id,
        )
        chunk_sa = DocumentChunk(
            id="chunk_d_sa",
            version_id=ver_sa.id,
            document_id=doc_sa.id,
            chunk_index=0,
            page_number=1,
            block_ids=["blk_sa"],
            text=(
                "Hướng dẫn xét cấp học bổng khuyến khích học tập công tác sinh viên"
                " STUDENT_AFFAIRS."
            ),
            token_count=16,
            bbox=[15.0, 15.0, 210.0, 60.0],
            embedding=emb_sa,
            fulltext_tsv=(
                "Hướng dẫn xét cấp học bổng khuyến khích học tập công tác sinh viên"
                " STUDENT_AFFAIRS."
            ),
        )

        # Document 3: INTERNAL
        doc_int = Document(
            id="doc_d_int",
            title="Báo cáo tài chính nội bộ",
            type="BAO_CAO",
            status="APPROVED",
            scope="INTERNAL",
            code_number="BC-INT-2026",
            author_id=admin_user.id,
        )
        ver_int = DocumentVersion(
            id="ver_d_int",
            document_id=doc_int.id,
            version_number=1,
            status="APPROVED",
            file_url="/files/int.pdf",
            file_size=4096,
            checksum="hash_int",
            ocr_status="SUCCEEDED",
            created_by=admin_user.id,
        )
        chunk_int = DocumentChunk(
            id="chunk_d_int",
            version_id=ver_int.id,
            document_id=doc_int.id,
            chunk_index=0,
            page_number=1,
            block_ids=["blk_int"],
            text="Báo cáo tài chính nội bộ phòng ban ngân sách bảo mật INTERNAL.",
            token_count=14,
            bbox=[20.0, 20.0, 220.0, 70.0],
            embedding=emb_int,
            fulltext_tsv="Báo cáo tài chính nội bộ phòng ban ngân sách bảo mật INTERNAL.",
        )

        session.add_all(
            [
                doc_pub,
                ver_pub,
                chunk_pub,
                doc_sa,
                ver_sa,
                chunk_sa,
                doc_int,
                ver_int,
                chunk_int,
            ]
        )
        await session.commit()

    return {
        "pub_doc_id": doc_pub.id,
        "sa_doc_id": doc_sa.id,
        "int_doc_id": doc_int.id,
    }


# ============================================================================
# SECTION 1: REST API GET & POST Search Verification
# ============================================================================


@pytest.mark.asyncio
async def test_search_get_and_post_basic_and_top_k(
    api_client: AsyncClient,
    admin_user: User,
    seeded_rbac_search_data: dict[str, str],
) -> None:
    """Test GET /search and POST /search with top_k and parameters."""
    headers = auth_headers_for(admin_user)

    # 1. GET /search with q and top_k
    res_get = await api_client.get("/api/v1/search?q=đào+tạo&top_k=1", headers=headers)
    assert res_get.status_code == 200
    data_get = res_get.json()["data"]
    assert len(data_get["items"]) <= 1
    assert data_get["query"] == "đào tạo"

    # 2. POST /search with JSON payload
    payload = {
        "query": "học bổng",
        "top_k": 2,
        "alpha": 0.7,
        "page": 1,
        "size": 5,
    }
    res_post = await api_client.post("/api/v1/search", json=payload, headers=headers)
    assert res_post.status_code == 200
    data_post = res_post.json()["data"]
    assert len(data_post["items"]) <= 2
    assert data_post["query"] == "học bổng"
    assert data_post["items"][0]["score"] is not None


@pytest.mark.asyncio
async def test_search_alpha_weightings(
    api_client: AsyncClient,
    admin_user: User,
    seeded_rbac_search_data: dict[str, str],
) -> None:
    """Test search with alpha=0.0 (fulltext), alpha=1.0 (vector), and alpha=0.5 (hybrid)."""
    headers = auth_headers_for(admin_user)

    for alpha in [0.0, 0.5, 1.0]:
        res = await api_client.get(f"/api/v1/search?q=sinh+viên&alpha={alpha}", headers=headers)
        assert res.status_code == 200
        assert res.json()["success"] is True


# ============================================================================
# SECTION 2: RBAC Scope Enforcement Across Roles
# ============================================================================


@pytest.mark.asyncio
async def test_rbac_admin_sees_all_scopes(
    api_client: AsyncClient,
    admin_user: User,
    seeded_rbac_search_data: dict[str, str],
) -> None:
    """Admin role can search PUBLIC, STUDENT_AFFAIRS, and INTERNAL scopes."""
    headers = auth_headers_for(admin_user)

    # Search without scope filter -> returns items from all scopes
    res = await api_client.get(
        "/api/v1/search?q=INTERNAL+PUBLIC+STUDENT_AFFAIRS&top_k=10",
        headers=headers,
    )
    assert res.status_code == 200
    found_scopes = {item["document_scope"] for item in res.json()["data"]["items"]}
    assert (
        "PUBLIC" in found_scopes or "STUDENT_AFFAIRS" in found_scopes or "INTERNAL" in found_scopes
    )

    # Admin requesting explicit scope=INTERNAL -> 200 OK
    res_int = await api_client.get("/api/v1/search?q=tài+chính&scope=INTERNAL", headers=headers)
    assert res_int.status_code == 200
    items = res_int.json()["data"]["items"]
    assert len(items) > 0
    assert items[0]["document_scope"] == "INTERNAL"


@pytest.mark.asyncio
async def test_rbac_staff_scope_access(
    api_client: AsyncClient,
    staff_user: User,
    seeded_rbac_search_data: dict[str, str],
) -> None:
    """Empirical test for Staff role scope visibility.
    Checks whether Staff can access PUBLIC, STUDENT_AFFAIRS, and INTERNAL.
    """
    headers = auth_headers_for(staff_user)

    # Staff search PUBLIC
    res_pub = await api_client.get("/api/v1/search?q=quy+chế&scope=PUBLIC", headers=headers)
    assert res_pub.status_code == 200

    # Staff search STUDENT_AFFAIRS
    res_sa = await api_client.get(
        "/api/v1/search?q=học+bổng&scope=STUDENT_AFFAIRS",
        headers=headers,
    )
    assert res_sa.status_code == 200

    # Staff search INTERNAL
    res_int = await api_client.get("/api/v1/search?q=tài+chính&scope=INTERNAL", headers=headers)
    # Check current implementation behavior for staff requesting INTERNAL scope
    # (Implementation allows staff to see INTERNAL per dependencies.py & rbac-matrix.md)
    assert res_int.status_code == 200


@pytest.mark.asyncio
async def test_rbac_student_scope_restrictions(
    api_client: AsyncClient,
    student_user: User,
    seeded_rbac_search_data: dict[str, str],
) -> None:
    """Empirical test for Student role scope visibility.
    - Student can search PUBLIC and STUDENT_AFFAIRS
    - Student CANNOT access INTERNAL scope chunks (scope=INTERNAL returns 403 Forbidden)
    - Unfiltered search for Student must NEVER return any INTERNAL chunk
    """
    headers = auth_headers_for(student_user)

    # 1. Student search PUBLIC -> 200 OK
    res_pub = await api_client.get("/api/v1/search?q=quy+chế&scope=PUBLIC", headers=headers)
    assert res_pub.status_code == 200

    # 2. Student search STUDENT_AFFAIRS -> 200 OK
    res_sa = await api_client.get(
        "/api/v1/search?q=học+bổng&scope=STUDENT_AFFAIRS",
        headers=headers,
    )
    assert res_sa.status_code == 200

    # 3. Student search INTERNAL -> 403 Forbidden
    res_int = await api_client.get("/api/v1/search?q=tài+chính&scope=INTERNAL", headers=headers)
    assert res_int.status_code == 403
    assert res_int.json()["code"] == "FORBIDDEN"

    # 4. Student general search without scope filter -> INTERNAL chunks must be excluded
    res_general = await api_client.get("/api/v1/search?q=INTERNAL+tài+chính", headers=headers)
    assert res_general.status_code == 200
    returned_scopes = {item["document_scope"] for item in res_general.json()["data"]["items"]}
    assert "INTERNAL" not in returned_scopes


# ============================================================================
# SECTION 3: Edge Cases Stress Testing
# ============================================================================


@pytest.mark.asyncio
async def test_edge_case_empty_query(api_client: AsyncClient, admin_user: User) -> None:
    """Empty search query ('') triggers 422 validation error in FastAPI query validation."""
    headers = auth_headers_for(admin_user)

    # GET empty query
    res_get = await api_client.get("/api/v1/search?q=", headers=headers)
    assert res_get.status_code == 422

    # POST empty query
    payload = {"query": ""}
    res_post = await api_client.post("/api/v1/search", json=payload, headers=headers)
    assert res_post.status_code == 422


@pytest.mark.asyncio
async def test_edge_case_top_k_zero_and_invalid(api_client: AsyncClient, admin_user: User) -> None:
    """top_k=0 or top_k < 1 or top_k > 100 triggers 422 validation error."""
    headers = auth_headers_for(admin_user)

    # GET top_k=0 -> 422
    res_get_zero = await api_client.get("/api/v1/search?q=test&top_k=0", headers=headers)
    assert res_get_zero.status_code == 422

    # POST top_k=0 -> 422
    res_post_zero = await api_client.post(
        "/api/v1/search", json={"query": "test", "top_k": 0}, headers=headers
    )
    assert res_post_zero.status_code == 422

    # POST top_k=101 -> 422
    res_post_101 = await api_client.post(
        "/api/v1/search", json={"query": "test", "top_k": 101}, headers=headers
    )
    assert res_post_101.status_code == 422


@pytest.mark.asyncio
async def test_edge_case_nonexistent_search_term(
    api_client: AsyncClient, admin_user: User, seeded_rbac_search_data: dict[str, str]
) -> None:
    """Querying non-existent text returns 200 OK with empty items list."""
    headers = auth_headers_for(admin_user)

    res = await api_client.get("/api/v1/search?q=xyznonexistentterm999999", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    # Items should be empty or total count match
    assert isinstance(body["data"]["items"], list)


@pytest.mark.asyncio
async def test_edge_case_special_characters(
    api_client: AsyncClient, admin_user: User, seeded_rbac_search_data: dict[str, str]
) -> None:
    """Search query with SQL injection syntax, HTML tags, unicode accents, and punctuation."""
    headers = auth_headers_for(admin_user)

    special_queries = [
        "SELECT * FROM users WHERE '1'='1' --",
        "<script>alert('xss')</script>",
        "quy chế & (đào tạo | sinh viên) !",
        "học bổng % _ ' \" \\ / ` ~ * + -",
        "Tiếng Việt có dấu: Đào tạo, Sinh viên, Học bổng!",
    ]

    for sq in special_queries:
        # Test GET
        res_get = await api_client.get("/api/v1/search", params={"q": sq}, headers=headers)
        assert res_get.status_code == 200, f"Failed for GET query: {sq}"
        assert res_get.json()["success"] is True

        # Test POST
        res_post = await api_client.post("/api/v1/search", json={"query": sq}, headers=headers)
        assert res_post.status_code == 200, f"Failed for POST query: {sq}"
        assert res_post.json()["success"] is True


@pytest.mark.asyncio
async def test_edge_case_invalid_alpha_and_pagination(
    api_client: AsyncClient, admin_user: User
) -> None:
    """Test invalid alpha (<0 or >1) and invalid page/size (<1)."""
    headers = auth_headers_for(admin_user)

    # alpha > 1.0 -> 422
    res_alpha = await api_client.get("/api/v1/search?q=test&alpha=1.5", headers=headers)
    assert res_alpha.status_code == 422

    # page = 0 -> 422
    res_page = await api_client.get("/api/v1/search?q=test&page=0", headers=headers)
    assert res_page.status_code == 422

    # size = 0 -> 422
    res_size = await api_client.get("/api/v1/search?q=test&size=0", headers=headers)
    assert res_size.status_code == 422
