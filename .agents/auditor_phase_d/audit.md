# Forensic Audit Report — Phase D (RAG & pgvector Search)

**Work Product**: Phase D implementation in `apps/api/`
**Profile**: General Project / Forensic Audit
**Date**: 2026-08-11
**Verdict**: VERDICT: INTEGRITY VIOLATION

---

## Executive Summary

An independent forensic audit was conducted on the Phase D implementation (RAG & pgvector Search) in `apps/api/`. 
The static code analysis confirmed that core algorithms, model schemas, services, tasks, and API routers contain **genuine logic** (pgvector cosine distance queries, PostgreSQL TSVector full-text search, RRF rank fusion, recursive chunking with bounding box envelopes, embedding strategy pattern, and RBAC scope filters) without facade implementations or hardcoded test bypasses.

However, during execution of the required verification suite, **`uv run ruff check app tests`** and **`uv run ruff format --check app tests`** failed due to 15 linter errors (14 E501 line-length violations and 1 F401 unused import) and 2 unformatted files in `tests/test_phase_d_challenger1.py` and `tests/test_phase_d_challenger2.py`.

Under strict forensic auditor rules, any check failure mandates a verdict of **`VERDICT: INTEGRITY VIOLATION`**.

---

## Forensic Check Results

| Check Name | Status | Details |
|---|---|---|
| **1. Source Code & Facade Inspection** | `PASS` | No hardcoded test outputs, dummy implementations, or test bypasses detected. Logic is authentic. |
| **2. Test Suite & Coverage (`pytest`)** | `PASS` | 186 passed, 4 skipped (Postgres offline on local runner). Coverage: **80.18%** (>= 80% threshold met). |
| **3. Type Safety (`mypy app`)** | `PASS` | Success: no issues found in 51 source files. |
| **4. Linter Check (`ruff check`)** | `FAIL` | 15 errors found in `tests/test_phase_d_challenger1.py` and `tests/test_phase_d_challenger2.py`. |
| **5. Format Check (`ruff format --check`)** | `FAIL` | 2 files require reformatting (`tests/test_phase_d_challenger1.py`, `tests/test_phase_d_challenger2.py`). |

---

## Detailed Findings

### 1. Code Inspection Findings (CLEAN)
- `app/models/document_chunk.py`: Uses `pgvector.sqlalchemy.Vector(1024)` with SQLite fallback `JSON`, explicit composite indexes (`ix_document_chunks_version_index`, `ix_document_chunks_document_page`), proper SQLAlchemy 2.x types.
- `alembic/versions/0005_document_chunks_pgvector.py`: Includes conditional pgvector extension creation, HNSW index (`vector_cosine_ops`), and GIN full-text index on `fulltext_tsv`.
- `app/services/embedding.py`: Clean Strategy Pattern implementation with `MockEmbeddingStrategy` (deterministic SHA-256 fallback) and `BGEM3EmbeddingStrategy` (HTTP request to BGE-M3 1024-dim API with fallback).
- `app/services/chunking.py`: Clean recursive chunking logic with min-max bounding box envelope computation `[x0, y0, x1, y1]`, token count calculation, page boundaries, and overlap handling.
- `app/worker/tasks.py`: Celery task `_async_index_document_chunks` handles idempotency (deleting old chunks before insertion) and populates `to_tsvector("simple", text)`.
- `app/modules/search/`: Router, service, and schemas correctly implement RRF hybrid ranking (`alpha * rrf_vector + (1 - alpha) * rrf_fulltext`) and RBAC scope filtering (`get_allowed_scopes_for_user`).

### 2. Linter & Formatting Failures (VIOLATIONS)

#### Failed Command 1: `uv run ruff check app tests`
```
tests\test_phase_d_challenger1.py:61:101: E501 Line too long (105 > 100)
tests\test_phase_d_challenger1.py:92:101: E501 Line too long (103 > 100)
tests\test_phase_d_challenger1.py:96:101: E501 Line too long (111 > 100)
tests\test_phase_d_challenger1.py:190:101: E501 Line too long (111 > 100)
tests\test_phase_d_challenger1.py:209:101: E501 Line too long (102 > 100)
tests\test_phase_d_challenger1.py:213:101: E501 Line too long (108 > 100)
tests\test_phase_d_challenger1.py:216:101: E501 Line too long (102 > 100)
tests\test_phase_d_challenger1.py:242:101: E501 Line too long (101 > 100)
tests\test_phase_d_challenger1.py:270:101: E501 Line too long (101 > 100)
tests\test_phase_d_challenger2.py:1:101: E501 Line too long (105 > 100)
tests\test_phase_d_challenger2.py:16:19: F401 [*] `httpx.Response` imported but unused
tests\test_phase_d_challenger2.py:50:101: E501 Line too long (105 > 100)
tests\test_phase_d_challenger2.py:65:101: E501 Line too long (110 > 100)
tests\test_phase_d_challenger2.py:87:101: E501 Line too long (107 > 100)
tests\test_phase_d_challenger2.py:310:101: E501 Line too long (105 > 100)

Found 15 errors.
```

#### Failed Command 2: `uv run ruff format --check app tests`
```
Would reformat: tests\test_phase_d_challenger1.py
Would reformat: tests\test_phase_d_challenger2.py
2 files would be reformatted, 78 files already formatted
```

---

## Verification Evidence Log

### Command 1: `uv run pytest --cov=app --cov-report=term-missing`
```
================== 186 passed, 4 skipped in 62.06s (0:01:02) ==================
TOTAL coverage: 80.18%
```

### Command 2: `uv run mypy app`
```
Success: no issues found in 51 source files
```

---

## Required Action Plan for Implementer
To resolve the integrity violation and achieve `VERDICT: CLEAN`:
1. Remove unused import `Response` from `tests/test_phase_d_challenger2.py` (line 16).
2. Run `uv run ruff format app tests` to format test files to fit line length limits.
3. Verify with `uv run ruff check app tests` and `uv run ruff format --check app tests`.
