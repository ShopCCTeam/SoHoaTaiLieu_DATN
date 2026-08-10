# ADR-0003: Auth Hardening — Refresh Rotation + Argon2id + Runtime Postgres Verification

> Status: **Proposed** (2026-08-09)
> Author: AI agent + user review
> Review: user 2026-08-10 — **conditional approval**, cần 10 sửa đổi trước khi execute

## Context

Phase 1 đã implement `/auth/login` + `/auth/me` với:
- Bcrypt cost 12 (passlib) — đã có sẵn.
- JWT access token (HS256, TTL 15 phút).
- 49 unit test pass với SQLite in-memory.
- Docker Compose file đã viết nhưng **chưa chạy trên máy local**.
- PROGRESS.md ghi "verified" nhưng mới chỉ ở mức unit/static, chưa runtime verification trên PostgreSQL thật.

User review (2026-08-09 + 2026-08-10) chỉ ra:

### Method issues (2026-08-09)
1. Auth contract **chưa hoàn chỉnh** — thiếu `/auth/refresh`, `/auth/logout`, refresh rotation, reuse detection, cookie integration test.
2. **Production config** fail-open (JWT secret = "dev-only...", MinIO = "minioadmin", cookie secure=false).
3. **`/health/ready`** luôn trả ready → không đáng tin cho K8s readiness probe.
4. **CI Backend** chỉ chạy SQLite test, không có postgres service + alembic upgrade + coverage threshold.
5. **Password hash**: argon2id memory-hard hơn, là recommended của OWASP 2024+.

### Security bugs trong plan (2026-08-10) — **ĐÃ SỬA**
1. ~~`rotate_session(raw_token, family_id)`~~ → lookup `family_id` từ DB bằng `token_hash`, không nhận từ client.
2. Family revocation phải commit/flush **trước** khi raise HTTP error — không được chỉ `flush()` rồi raise (sẽ bị rollback).
3. Rotation phải dùng `SELECT ... FOR UPDATE` hoặc atomic conditional update để chống concurrent refresh.
4. Bỏ hoàn toàn migration verification bằng SQLite — migration dùng PG UUID + INET + pgcrypto.
5. Test reuse detection phải có assertion thật + pytest.raises.
6. Contract phải sync với OpenAPI: `/auth/refresh` trả `{access_token, expires_in}`, `/auth/logout` trả `204 No Content`.
7. Dùng valid Argon2id dummy hash (không phải bcrypt dummy); demo bcrypt hashes cần reset/reseed.
8. Mỗi commit phải build/test được — gộp atomic password migration vào 1 commit.
9. Commit ADR **trước** implementation, không để cuối.
10. Bổ sung: cookie attributes, Origin/CSRF check, `is_active` user check, audit log events.

## Decision

### Phase split rõ ràng

| Phase | Nội dung | Gate |
|---|---|---|
| **Phase 1.1** — Auth Implementation | argon2id, refresh sessions model, rotation service, auth routes, config fail-closed, health/ready, seed guard, CI | Static + Unit |
| **Phase 1.2** — Runtime Verification | docker stack lên, alembic upgrade/downgrade trên PG thật, oasdiff CI, integration test | Postgres + Docker + CI |
| **Phase 1 Hoàn chỉnh** | Cả 1.1 + 1.2 | Cả 5 gate |

**Không ghi "VERIFIED" cho toàn bộ Phase 1 cho đến khi cả 5 gate pass.**

### Quyết định kiến trúc

| # | Quyết định | Lý do |
|---|---|---|
| D1 | Thêm **refresh token rotation** với **opaque random token** (không JWT), lưu hash SHA-256 trong DB. `family_id` lookup từ DB, không client gửi. | Opaque đơn giản hơn JWT revocation; rotation phát hiện token bị đánh cắp qua reuse |
| D2 | Refresh token set trong **HttpOnly + SameSite=Lax + Secure(prod) + Path=/api/v1/auth + Max-Age** | Bảo vệ khỏi XSS; rule 06 đã chốt |
| D3 | **Reuse detection** → commit family revocation trước khi trả 401 → thu hồi **TOÀN BỘ family** (NIST 800-63B) | An toàn hơn chỉ thu hồi 1 token |
| D4 | Dùng **atomic rotation**: `SELECT ... FOR UPDATE` hoặc conditional `UPDATE ... WHERE id=:id AND revoked_at IS NULL RETURNING id` — chỉ 1 request tạo được token mới | Chống concurrent refresh attack |
| D5 | Đổi `bcrypt` (passlib) → **`pwdlib[argon2]`** (argon2id, `PasswordHash.recommended()`) | OWASP 2024 recommendation; argon2id memory-hard |
| D6 | **Dummy hash**: tạo valid Argon2id hash cố định để timing defense cho email-not-found flow | Tránh timing oracle leak khi email không tồn tại |
| D7 | **Demo data**: reset/reseed bcrypt users → argon2id sau khi chuyển hashing | Không có production user, reset dev data phù hợp hơn hash migration |
| D8 | `config.py` **fail-closed ở production**: reject default secret, `localhost` CORS, `secure=false` cookie | Defense-in-depth; rule 06 |
| D9 | `/health/ready` → `SELECT 1` thật tới Postgres; trả **503** nếu fail | K8s readiness probe cần chính xác |
| D10 | **Bổ sung audit log events** cho security actions | Structured security log + note audit_logs table còn pending |
| D11 | **Logout idempotent**: token valid → revoke + clear; token invalid/missing → vẫn clear cookie + trả 204 | OAuth 2.0 BCP |
| D12 | **Refresh check user.is_active**: nếu user bị disable → revoke family + trả 401 | Bảo vệ tài khoản bị khóa |
| D13 | Bổ sung **Postgres 16 service** vào GitHub Actions `api` job; chạy `alembic upgrade head` + `--cov-fail-under=80` | Rule 05 coverage + evidence runtime |
| D14 | **oasdiff** kích hoạt trong CI: compare `docs/api/openapi.yaml` vs `app.openapi()` → fail nếu breaking change | Rule 03 contract-first |
| D15 | `seed.py` guard `APP_ENV ∈ {development, test}`; refuse ở production/staging | Tránh seed nhầm vào prod |
| D16 | Makefile dùng `docker compose up -d --build --wait` thay vì manual sleep | `--wait` đợi healthcheck |

### Out of scope

- ❌ `/documents` GET (Phase 2).
- ❌ Celery worker + MinIO upload (Phase 3).
- ❌ OCR (Phase 4).
- ❌ RAG/pgvector (Phase 5).
- ❌ ML training (parallel track).
- ❌ Persistent `audit_logs` table — dùng structured security log trong Phase 1.1; ghi rõ pending.

### Schema: `refresh_sessions`

```sql
CREATE TABLE refresh_sessions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  family_id       UUID NOT NULL,
  token_hash      VARCHAR(64) NOT NULL UNIQUE,   -- SHA-256 hex
  user_agent      VARCHAR(512) NULL,
  ip_address      INET NULL,
  issued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at      TIMESTAMPTZ NOT NULL,
  revoked_at      TIMESTAMPTZ NULL,
  replaced_by_id  UUID NULL REFERENCES refresh_sessions(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_refresh_sessions_user_id      ON refresh_sessions(user_id);
CREATE INDEX ix_refresh_sessions_family_id    ON refresh_sessions(family_id);
CREATE INDEX ix_refresh_sessions_token_hash   ON refresh_sessions(token_hash);
CREATE INDEX ix_refresh_sessions_expires_at   ON refresh_sessions(expires_at);
CREATE INDEX ix_refresh_sessions_revoked_at   ON refresh_sessions(revoked_at);
```

### API contract (sync với OpenAPI — source of truth)

| Endpoint | Verb | Auth | Body | Response | Cookie set |
|---|---|---|---|---|---|
| `/api/v1/auth/login` | POST | none | `{email, password}` | `200 {access_token, expires_in, user}` | `rt=<opaque>; HttpOnly; SameSite=Lax; Secure(prod); Path=/api/v1/auth; Max-Age=604800` |
| `/api/v1/auth/refresh` | POST | cookie `rt` | none | `200 {access_token, expires_in}` | `rt=<new-opaque>` (rotate) |
| `/api/v1/auth/logout` | POST | cookie `rt` | none | `204 No Content` | `rt=` (clear) |
| `/api/v1/auth/me` | GET | Bearer | none | `200 {user}` | none |

### Security log events

Phase 1.1 dùng structured JSON log (audit_logs table pending):

| Event | Log level | Content |
|---|---|---|
| `auth.login.success` | INFO | user_id, ip, user_agent |
| `auth.login.failed` | WARNING | email (hash), reason, ip |
| `auth.refresh.rotated` | INFO | user_id, family_id |
| `auth.refresh.reuse_detected` | ERROR | family_id, ip — **IMMEDIATE ALERT** |
| `auth.refresh.expired` | WARNING | family_id |
| `auth.refresh.inactive_user` | WARNING | user_id |
| `auth.logout` | INFO | user_id |
| `auth.session.family_revoked` | INFO | family_id, reason (logout / reuse / inactive) |

### Verify gate

Phase 1.1 implementation chỉ done khi CẢ 2 gate:

| Gate | Tiêu chí | Command |
|---|---|---|
| Static | ruff + mypy strict + 0 warning | `uv run ruff check . && uv run ruff format --check . && uv run mypy app` |
| Unit | pytest pass + coverage ≥ 80% | `uv run pytest --cov=app --cov-fail-under=80` |

Phase 1.2 Runtime Verification:

| Gate | Tiêu chí | Command |
|---|---|---|
| **Postgres** | alembic upgrade/downgrade/upgrade trên PG thật | `docker exec ctsv-api uv run alembic upgrade head && ... downgrade -1 && ... upgrade head` |
| **Docker** | `make up` + `make seed` + curl login/refresh/logout | manual |
| **CI** | GitHub Actions api job pass | push → CI run |

**Toàn bộ Phase 1 chỉ VERIFIED khi cả 5 gate pass.**

## Consequences

### Tích cực
- Auth đủ chuẩn production (rotation + reuse detection + cookie).
- Config fail-closed ngăn leak secret mặc định.
- Health check thật → K8s rollout chính xác.
- CI phát hiện regression sớm.

### Tiêu cực / Rủi ro
- ⚠️ Phase 1.1 estimate tăng ~30-40% do bug fix (rotation atomic, rollback persistence).
- ⚠️ pwdlib dependency mới → pin `pwdlib[argon2]>=0.2.0,<0.3`.
- ⚠️ Demo users bcrypt hashes → reset dev DB và reseed sau khi chuyển argon2id.
- ⚠️ Docker chưa có trên máy → user verify Phase 1.2 gate thủ công.
- ⚠️ Audit log dùng structured log; persistent `audit_logs` table còn pending.

### Rollback

Nếu Phase 1.1 fail → **không reset shared branch**. Thay vào đó:
- `git revert <bad-commit>` hoặc forward-fix trên branch.
- Nếu migration 0002 chưa merged → forward-fix trên branch.
- Không `git reset --hard`.

## Ref

- Rule `.cursor/rules/06-security.mdc` — auth + cookie + audit.
- Rule `.cursor/rules/04-database-rag-ocr.mdc` — schema convention.
- Rule `.cursor/rules/05-testing.mdc` — coverage + integration.
- Rule `.cursor/rules/08-governance.mdc` — agent permission + idempotency.
- NIST 800-63B Session Management (reuse detection).
- OWASP Password Storage Cheat Sheet 2024 (argon2id).
- pwdlib docs: https://github.com/ya-mat/pwdlib
- OAuth 2.0 BCP: logout idempotent.