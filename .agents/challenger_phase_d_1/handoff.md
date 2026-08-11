# Phase D Search & RBAC Empirical Verification Handoff Report

## 1. Observation

### 1.1 Empirical Verification Test Execution Results (Challenger 1 Suite)
Executed 10 empirical test cases written in `apps/api/tests/test_phase_d_challenger1.py`:
- Command: `uv run pytest tests/test_phase_d_challenger1.py`
- Result: **10 passed in 3.11s** (100% pass rate).

### 1.2 Full Suite Execution & Concurrent Test Suite Findings
Executed full backend test suite in `apps/api`:
- Command: `uv run pytest`
- Total tests collected: 208
- Results: **200 passed, 4 skipped, 3 failed, 1 error**.

**Failure Breakdown observed in `tests/test_phase_d_challenger2.py`**:
1. `ValueError: min() iterable argument is empty` in `app/services/chunking.py:45` when `compute_envelope_bbox` is passed bboxes where no item has `len(b) >= 4`.
2. `ModuleNotFoundError: No module named 'alembic.versions'` when dynamically loading Alembic script in `test_alembic_0005_upgrade_downgrade_script_execution`.
3. `RESPX: <Request(b'POST', 'http://bge-m3.test/embed')> not mocked!` in `test_bge_m3_embedding_strategy_success_and_fallback`.
4. `fixture 'script_dir' not found` error in `test_alembic_0005_migration_revision_chain`.

### 1.3 Detailed Empirical Observations for Search & RBAC (Challenger 1 Scope)

#### A. Search REST APIs (`GET /api/v1/search` & `POST /api/v1/search`)
1. **Parameter Handling**:
   - `GET /api/v1/search?q=...` accepts query parameters `q`, `scope`, `type`, `alpha` (default 0.5), `top_k` (default 10), `page` (default 1), `size` (default 10).
   - `POST /api/v1/search` accepts JSON body `{ "query", "scope", "doc_type", "alpha", "top_k", "page", "size" }`.
   - Both endpoints wrap search results in `SearchEnvelope` with standard structure:
     `{"success": true, "data": {"items": [...], "total": N, "page": 1, "size": 10, "query": "..."}}`.
2. **Result Limits & RRF Weightings**:
   - `top_k` parameter limits returned candidates.
   - `alpha` parameter successfully scales RRF score fusion between full-text search ranks (`alpha=0.0`) and vector similarity ranks (`alpha=1.0`).
3. **Document ID Filtering**:
   - Schema observation: `SearchQueryRequest` and `search_documents_get` filter by `scope` and `doc_type`/`type`, but do not define explicit `document_ids` or `document_id` query parameters in the OpenAPI contract.

#### B. RBAC Scope Enforcement
1. **Admin Role (`admin`)**:
   - Allowed scopes: `PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`.
   - Admin can view chunks across all scopes and explicitly request `scope=INTERNAL` without 403 Forbidden.
2. **Staff Role (`staff`)**:
   - Allowed scopes: `PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL` (per `app/modules/documents/dependencies.py:14-26` and `docs/domain/rbac-matrix.md:19-20`).
   - Staff can view chunks from `PUBLIC`, `STUDENT_AFFAIRS`, and `INTERNAL`.
3. **Student Role (`student`)**:
   - Allowed scopes: `PUBLIC`, `STUDENT_AFFAIRS`.
   - Explicit request `GET /search?q=...&scope=INTERNAL` by Student returns **HTTP 403 Forbidden** (`code: "FORBIDDEN"`).
   - Unfiltered search queries by Student execute DB filter `Document.scope.in_(["PUBLIC", "STUDENT_AFFAIRS"])`, completely excluding `INTERNAL` chunks.
   - Student CAN access `STUDENT_AFFAIRS` chunks (as specified in `docs/domain/rbac-matrix.md:12` and `app/modules/documents/dependencies.py:26`).

#### C. Edge Cases & Stress Testing
1. **Empty Query (`q=""` or `query=""`)**:
   - Returns **HTTP 422 Unprocessable Entity** (FastAPI Pydantic schema validation `min_length=1`).
2. **Invalid `top_k` (`top_k=0` or `top_k > 100`)**:
   - Returns **HTTP 422 Unprocessable Entity** (`ge=1, le=100` validation).
3. **Non-Existent Query Terms (`q="xyznonexistentterm999999"`)**:
   - Returns **HTTP 200 OK** with `items: []` and `total: 0` without server exceptions.
4. **Special Characters & Attack Vectors**:
   - SQL Injection strings (e.g. `SELECT * FROM users WHERE '1'='1' --`), XSS tags (`<script>alert('xss')</script>`), Vietnamese unicode accents (`Đào tạo, Sinh viên`), and complex punctuation execute safely with **HTTP 200 OK**.
5. **Out-of-Range Parameters**:
   - `alpha = 1.5` or `alpha = -0.5` -> **HTTP 422 Unprocessable Entity** (`ge=0.0, le=1.0`).
   - `page = 0` or `size = 0` -> **HTTP 422 Unprocessable Entity** (`ge=1`).

---

## 2. Logic Chain

1. **Observation**: `GET /api/v1/search` and `POST /api/v1/search` successfully execute RRF hybrid search and return structured JSON responses, passing all tests in `test_phase_d_challenger1.py`.
   -> **Inference**: The search REST endpoints are fully functional and handle parameter inputs accurately.
2. **Observation**: When Student role sends `scope=INTERNAL`, API responds with HTTP 403 Forbidden. When Student role sends general search queries, `Document.scope.in_(["PUBLIC", "STUDENT_AFFAIRS"])` is appended to the SQL query.
   -> **Inference**: RBAC scope isolation is enforced at both API dependency layer and database query layer for Student role.
3. **Observation**: Staff role and Admin role have `allowed_scopes = ["PUBLIC", "STUDENT_AFFAIRS", "INTERNAL"]` per `app/modules/documents/dependencies.py` line 20 and `docs/domain/rbac-matrix.md` line 19-20.
   -> **Inference**: Staff role behavior conforms to the project RBAC matrix specification (`INTERNAL` scope accessible by staff and admin).
4. **Observation**: Inputting `q=""`, `top_k=0`, `top_k=101`, `alpha=1.5`, `page=0` returns HTTP 422 Unprocessable Entity. Inputting SQL/XSS payloads returns HTTP 200 with sanitized query processing.
   -> **Inference**: Input validation and parameter boundary enforcement for Search REST APIs are robust.
5. **Observation**: `ChunkingService.compute_envelope_bbox` raises `ValueError` if passed a list containing only empty/invalid bboxes (`len(b) < 4`).
   -> **Inference**: `compute_envelope_bbox` lacks empty-sequence guard if filtering removes all bboxes.

---

## 3. Caveats

1. **Postgres pgvector vs SQLite Fallback**: Unit and integration tests in the test suite run against SQLite in-memory with Python cosine similarity calculation fallback (`_cosine_similarity`). Full pgvector `<->` vector distance indexing and PostgreSQL `fulltext_tsv` `ts_rank` triggers should be verified in local Docker environment (`make up`) during staging deployment.
2. **Explicit `document_ids` Filter**: Search endpoints filter by document scope (`scope`) and document category (`type`/`doc_type`), but currently do not expose a `document_ids` array parameter in `SearchQueryRequest`.

---

## 4. Conclusion

**Verdict**: **Search REST APIs & RBAC Scope Enforcement PASS** (with minor edge-case finding in Chunking bbox calculation).

Search REST APIs, RRF hybrid ranking, RBAC scope enforcement, and input boundary conditions passed all tests in `test_phase_d_challenger1.py`.

---

## 5. Verification Method

To independently verify these findings:

1. Change directory to API project root:
   ```bash
   cd E:\SoHoaTaiLieu_DATN\apps\api
   ```
2. Run the Phase D Challenger 1 verification test suite:
   ```bash
   uv run pytest tests/test_phase_d_challenger1.py
   ```
   *Expected result*: 10 passed in ~3.1s.
