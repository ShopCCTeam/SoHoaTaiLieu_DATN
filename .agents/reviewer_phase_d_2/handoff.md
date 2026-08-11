# Handoff Report — Reviewer 2 Phase D (RAG Vector Search Engine)

**Verdict**: **PASS**

---

## 1. Observation

### Codebase & Files Inspected
- `apps/api/app/modules/search/router.py` (lines 1–93): Search API endpoints `GET /search` and `POST /search`.
- `apps/api/app/modules/search/service.py` (lines 1–201): RRF Hybrid Search service and SQLite fallback implementation.
- `apps/api/app/modules/search/schemas.py`: Input requests (`SearchQueryRequest`) and response envelopes (`SearchEnvelope`, `SearchResultItem`).
- `apps/api/app/services/chunking.py` (lines 1–201): `ChunkingService` and `compute_envelope_bbox` implementation.
- `apps/api/app/models/document_chunk.py` (lines 1–109): `DocumentChunk` model with `.with_variant(...)` for SQLite/PG compatibility.
- `apps/api/app/modules/documents/dependencies.py` (lines 14–26): `get_allowed_scopes_for_user(user)` RBAC scope definition.
- `apps/api/tests/test_search.py` (lines 1–263): Integration tests for search endpoints and RBAC scope filtering.
- `apps/api/tests/test_chunking.py` (lines 1–105): Unit tests for chunking service and bounding box calculation.

### Verbatim Tool Command Execution Results

1. **`uv run pytest`**:
   ```
   =========================== short test summary info ===========================
   SKIPPED [1] tests\test_alembic.py:121: Postgres không khả dụng tại localhost:5432: TimeoutError('timed out')
   SKIPPED [1] tests\test_models_pg.py:24: Postgres không khả dụng: ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection
   SKIPPED [1] tests\test_models_pg.py:63: Postgres không khả dụng: ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection
   SKIPPED [1] tests\test_models_pg.py:138: Postgres không khả dụng: ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection
   ======================= 186 passed, 4 skipped in 52.16s =======================
   ```

2. **`uv run ruff check app tests`**:
   ```
   All checks passed!
   ```

3. **`uv run ruff format --check app tests`**:
   ```
   78 files already formatted
   ```

4. **`uv run mypy app`**:
   ```
   Success: no issues found in 51 source files
   ```

---

## 2. Logic Chain

1. **Security & Authorization (RBAC Scope Filtering)**:
   - Observation: `router.py` lines 42–48 & 73–79 invoke `get_allowed_scopes_for_user(current_user)`. If a user requests a scope not allowed for their role (e.g. `student` requesting `INTERNAL`), an HTTP 403 Forbidden exception is raised.
   - Observation: `service.py` lines 61–65 applies `.where(Document.deleted_at.is_(None)).where(Document.scope.in_(allowed_scopes))`. Unrequested queries strictly default to the user's role-allowed scopes.
   - Conclusion: Multi-layered RBAC scope enforcement is active and secure against scope escalation.

2. **Search Scoring (Reciprocal Rank Fusion - RRF $k=60$)**:
   - Observation: `service.py` lines 130–162 calculates RRF scores using $k=60$:
     `rrf_v = (1.0 / (k_const + r_v))` and `rrf_f = (1.0 / (k_const + r_f))`.
   - Observation: Combined score `rrf_score = alpha * rrf_v + (1.0 - alpha) * rrf_f` balances vector similarity ($\alpha=1.0$) and full-text search ($\alpha=0.0$) with default $\alpha=0.5$.
   - Conclusion: Algorithm strictly follows standard RRF formulation ($k=60$) and properly handles candidate merging and sub-score propagation.

3. **Chunking BBox (Min-Max Envelope Calculation)**:
   - Observation: `chunking.py` lines 41–54 defines `compute_envelope_bbox(bboxes)`:
     calculating `min(x0)`, `min(y0)`, `max(x1)`, `max(y1)` rounded to 2 decimal places.
   - Observation: `test_chunking.py` lines 8–16 confirms envelope bounding box for overlapping blocks `[[10, 20, 100, 50], [5, 30, 120, 90], [15, 10, 80, 40]]` returns `[5.0, 10.0, 120.0, 90.0]`.
   - Conclusion: Bounding box aggregation correctly reflects the spatial span of merged OCR text blocks.

4. **Dual Database Dialect (`_Vector(1024)` & `_TSVector`)**:
   - Observation: `document_chunk.py` lines 81–90 configures `Vector(1024).with_variant(JSON, "sqlite")` and `TSVECTOR().with_variant(Text, "sqlite")`.
   - Observation: `service.py` lines 52–54 dynamically inspects DB dialect (`"postgresql" in str(bind.dialect.name)`). It uses native `cosine_distance` and `ts_rank` on PostgreSQL, while providing clean Python cosine similarity and term matching fallbacks for SQLite.
   - Conclusion: Dual dialect support provides seamless test execution on SQLite while maintaining high-performance native PG vector & full-text search in production.

5. **Code & Integrity Quality**:
   - Observation: No hardcoded test results, facade implementations, or bypasses were detected in `app/` or `tests/`.
   - Observation: All 4 verification commands passed (186 unit/integration tests passed, Ruff clean, Mypy clean).

---

## 3. Caveats

- **PostgreSQL Integration Tests Skipped in Dev Environment**: `tests/test_models_pg.py` and `tests/test_alembic.py` (4 tests) were skipped because PostgreSQL container was not running locally at localhost:5432. This is expected behavior outside Docker CI environments.

---

## 4. Conclusion

Phase D (RAG Vector Search Engine) implementation meets all functional, security, algorithmic, and code quality requirements. **Verdict: PASS**.

---

## 5. Verification Method

To independently re-verify this report:
```bash
cd apps/api
uv run pytest
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
```
Invalidation conditions: Any test failure, lint violation, type check error, or unauthorized access to `INTERNAL` scope document chunks by `student` role users.
