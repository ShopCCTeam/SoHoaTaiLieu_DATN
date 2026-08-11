# Backlog — Auth Phase Nâng Cao

> Những task chưa làm, có thể thực hiện ở phase sau.
> KHÔNG commit code — chỉ ghi backlog.

---

## B1 — Coverage Gate Per-Module

**Mô tả**: Đặt `coverage` threshold cho từng module riêng biệt, không phải project-wide average.

**Lý do**: Một số module có logic phức tạp (auth rotation, RAG pipeline) cần ≥90% coverage; một số module chỉ có wiring/dumb pass-through (routes đã test ở integration) chỉ cần ≥60%.

**Cách làm**:
- Thêm `pyproject.toml` section `[tool.coverage.report]`
- Module-level gates: `app/modules/auth/`: 80%, `app/modules/rag/`: 80%, `app/api/`: 70%, `app/core/`: 60%
- Chạy `coverage` trong CI, fail nếu threshold không đạt

**Trạng thái**: Auth coverage hiện tại **75.38%** (2026-08-11). Gate CI đặt tạm ở 75%. Nâng dần theo từng sprint, KHÔNG hạ.

**Ratchet log**:
| Ngày | Coverage | Ghi chú |
|---|---|---|
| 2026-08-11 | 75.38% | Baseline — chưa cover refresh_service family rotation logic |

---

## B7 — Docstring `_INet` trong `test_models_pg.py`

**Mô tả**: Sửa 2 lỗi docstring trong `test_models_pg.py` (tên test không mô tả đúng INET, thiếu import asyncpg).

**Lý do**: Ngày 2026-08-10 đã nêu, nhưng chưa ưu tiên.

**Cách làm**:
- Sửa docstring: `test_refresh_session_inet_roundtrip_on_postgres` → mô tả INET, không phải IP string
- Thêm `import asyncpg` (InvalidCatalogNameError) trong test nếu dùng `pg_engine` với skip logic mở rộng
- Không blocking PR — chuyển sang phase OCR/RAG trước

---

## B2 — Test Concurrency FOR UPDATE trên PostgreSQL

**Mô tả**: Viết test concurrency thật — 2 request refresh đồng thời với cùng 1 refresh token trên PostgreSQL.

**Lý do**: `SELECT FOR UPDATE` lock trong `refresh_service.py` chỉ chạy đúng trên PG thật. SQLite không có row-level locking. Test hiện tại là sequential.

**Cách làm**:
- Tạo `tests/test_concurrency.py` dùng `pg_engine` fixture
- Dùng `asyncio.gather` gửi 2 request refresh đồng thời
- Assert: chỉ 1 thành công, 1 nhận `AUTH_REFRESH_REUSE_DETECTED` (hoặc `AUTH_REFRESH_INVALID`)
- Assert: chỉ 1 session mới được tạo trong DB

---

## B3 — `_INet.process_result_value`

**Mô tả**: Kiểm tra `process_result_value` xử lý đúng khi PG trả về `inet` object.

**Lý do**: `process_result_value` trong `_INet` TypeDecorator hiện chỉ trả về `value` (có thể là `ipaddress` object từ PG). Cần verify trả về `str` để đồng nhất với SQLite.

**Cách làm**:
```python
def process_result_value(self, value: Any, dialect: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    # PG trả về ipaddress object
    return str(value)
```
- Thêm test trong `test_models_pg.py` để verify IPv4/IPv6 string sau khi roundtrip

---

## B4 — `revoke_family` Public + Dùng `reason`

**Mô tả**: Expose `revoke_family` trong public API và truyền `reason` vào audit log.

**Lý do**: Hiện tại `_revoke_family` là private. Nếu sau này cần revoke family từ admin panel (force logout user) thì cần gọi được từ router/service khác.

**Cách làm**:
- Đổi tên `_revoke_family` → `revoke_family` (public)
- Thêm `reason` parameter
- Audit log trong `router.py` ghi `reason` khi revoke family (reuse detection)
- Test `revoke_family` với reason

---

## B5 — Bỏ `assert user is not None` + Di chuyển S101 xuống per-file

**Mô tả**: Thay `assert` trong router bằng guard có message rõ ràng, hoặc bỏ nếu redundant. Di chuyển `noqa: S101` comment xuống file test thay vì global.

**Lý do**: 
- `assert` không an toàn trong production (bị `-O` strip) — nên dùng explicit check
- `noqa: S101` trong `router.py` blanket抑制 toàn bộ file, nên đặt ở từng dòng hoặc trong `pyproject.toml`

**Cách làm**:
- Thay `assert user is not None, "..."` trong login bằng:
  ```python
  if user is None:
      raise RuntimeError("authenticate returned OK but user is None — internal error")
  ```
  Hoặc bỏ hoàn toàn nếu type checker đã đảm bảo
- Thêm vào `pyproject.toml`:
  ```toml
  [tool.ruff.per-file-ignores]
  "tests/**" = ["S101"]  # allow asserts in tests
  "app/modules/auth/router.py" = []  # remove blanket ignore
  ```
  Sau đó chỉ `noqa` ở từng dòng cần thiết

---

## B6 — Dọn Dead Code: `_extract_refresh_cookie` + `asyncio.sleep(2)` → `freezegun`

**Mô tả**: Xoá `_extract_refresh_cookie` trong `test_auth_router.py` (dead code), thay `asyncio.sleep(2)` bằng `freezegun` để test token expiry nhanh hơn.

**Lý do**:
- `_extract_refresh_cookie` trùng với `_extract_rt_cookie` — dead code
- `asyncio.sleep(2)` chậm (2 giây/test), flaky nếu máy load nặng
- `freezegun` (hoặc `time-machine`) freeze time → test expiry tức thì

**Cách làm**:
- Xoá `_extract_refresh_cookie` helper
- Thay `await asyncio.sleep(2)` trong `test_me_with_expired_token_returns_401` bằng:
  ```python
  from freezegun import freeze_time
  with freeze_time("2025-01-01 12:00:00"):
      # tạo token expired
  ```
- Thêm `freezegun` vào `pyproject.toml` `[tool.poetry.group.dev.dependencies]`
