# ADR-0003: Auth Hardening — Refresh Rotation + Argon2id + Runtime Postgres Verification

> Status: **Proposed** (2026-08-09)
> Author: AI agent + user review

## Context

Phase 1 đã implement `/auth/login` + `/auth/me` với:
- Bcrypt cost 12 (passlib) — đã có sẵn.
- JWT access token (HS256, TTL 15 phút).
- 49 unit test pass với SQLite in-memory.
- Docker Compose file đã viết nhưng **chưa chạy trên máy local**.
- README + PROGRESS.md ghi "verified" nhưng mới chỉ ở mức unit/static, chưa có runtime verification trên PostgreSQL thật.

User review (2026-08-09) chỉ ra các vấn đề method:
1. Auth contract **chưa hoàn chỉnh** — thiếu `/auth/refresh`, `/auth/logout`, refresh rotation, reuse detection, cookie integration test.
2. **Production config** chấp nhận default value nhạy cảm (JWT secret = "dev-only...", MinIO = "minioadmin", refresh cookie secure=false) → fail-open thay vì fail-closed.
3. **`/health/ready`** luôn trả ready bất kể Postgres sống hay chết → không đáng tin cho K8s readiness probe.
4. **CI Backend** chỉ chạy SQLite test, không có postgres service + alembic upgrade + integration test + coverage threshold.
5. **Password hash**: bcrypt ổn nhưng passlib có history không tương thích với bcrypt 4.x; argon2id memory-hard hơn, là recommended của OWASP 2024+.
6. **PROGRESS.md** có duplicate heading, badge "verified" mơ hồ, chưa tách rõ static/unit/postgres/docker/CI.

## Decision

Chốt Phase 1.1 = **Auth completion + Runtime hardening** trước khi sang Phase 2 (Documents).

### Quyết định kiến trúc

| # | Quyết định | Lý do |
|---|---|---|
| D1 | Thêm **refresh token rotation** với **opaque random token** (không JWT), lưu hash SHA-256 trong DB | Opaque đơn giản hơn JWT revocation; rotation phát hiện token bị đánh cắp qua reuse |
| D2 | Refresh token set trong **HttpOnly + SameSite=Lax + Secure cookie** (`refresh_cookie_*` đã có trong config) | Bảo vệ khỏi XSS; rule 06 đã chốt pattern này |
| D3 | **Reuse detection** → thu hồi **TOÀN BỘ family** (NIST 800-63B Session Management) | An toàn hơn chỉ thu hồi 1 token |
| D4 | Đổi `bcrypt` (passlib) → **`pwdlib[argon2]`** (argon2id, m=64MB, t=3, p=4) | Argon2id là OWASP 2024 recommendation; passlib có vấn đề compat với bcrypt 4.x |
| D5 | `config.py` phải **fail-closed ở production**: reject default secret, weak password, `localhost` CORS, `secure=false` cookie | Defense-in-depth; rule 06 đã yêu cầu |
| D6 | `/health/ready` → chạy `SELECT 1` thật tới Postgres; trả **503 Service Unavailable** nếu fail | K8s readiness probe cần chính xác |
| D7 | Bổ sung **Postgres 16 + pgvector service** vào GitHub Actions `api` job; chạy `alembic upgrade head` + integration test + `--cov-fail-under=80` | Rule 05 đã yêu cầu coverage; CI mới có evidence runtime thật |
| D8 | **oasdiff** kích hoạt thật trong CI: compare `docs/api/openapi.yaml` (contract) vs `app.openapi()` (runtime) → fail nếu breaking change | Rule 03 chốt contract-first |
| D9 | `seed.py` phải guard `APP_ENV ∈ {development, test}`; refuse ở production/staging | Tránh seed nhầm vào prod |
| D10 | Makefile dùng `docker compose up -d --build --wait` thay vì manual sleep 10s | `--wait` đợi healthcheck xong |

### Quyết định không làm (out of scope Phase 1.1)

- ❌ `/documents` GET (Phase 2).
- ❌ Celery worker + MinIO upload (Phase 3).
- ❌ OCR (Phase 4).
- ❌ RAG/pgvector (Phase 5).
- ❌ ML training (parallel track).

### Schema mới: `refresh_sessions`

```sql
CREATE TABLE refresh_sessions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  family_id       UUID NOT NULL,             -- nhóm rotation chain; reuse → revoke whole family
  token_hash      VARCHAR(64) NOT NULL,      -- SHA-256 hex của opaque token
  user_agent      VARCHAR(512) NULL,          -- audit
  ip_address      INET NULL,                  -- audit
  issued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at      TIMESTAMPTZ NOT NULL,       -- = issued_at + JWT_REFRESH_TOKEN_TTL_SECONDS
  revoked_at      TIMESTAMPTZ NULL,           -- set khi rotate / logout / reuse detection
  replaced_by_id  UUID NULL REFERENCES refresh_sessions(id),  -- chain khi rotate
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_refresh_sessions_user_id     ON refresh_sessions(user_id);
CREATE INDEX ix_refresh_sessions_family_id   ON refresh_sessions(family_id);
CREATE INDEX ix_refresh_sessions_token_hash  ON refresh_sessions(token_hash);
CREATE INDEX ix_refresh_sessions_expires_at  ON refresh_sessions(expires_at);
CREATE INDEX ix_refresh_sessions_revoked_at  ON refresh_sessions(revoked_at);
```

### API contract mới

| Endpoint | Verb | Auth | Body | Response | Cookie set |
|---|---|---|---|---|---|
| `/api/v1/auth/login` | POST | none | `{email, password}` | `{access_token, expires_in, user}` | `rt=<opaque>; HttpOnly; SameSite=Lax; Secure(prod)` |
| `/api/v1/auth/refresh` | POST | cookie `rt` | none | `{access_token, expires_in, user}` | `rt=<new-opaque>` (rotate) |
| `/api/v1/auth/logout` | POST | cookie `rt` | none | `{}` | `rt=` (clear cookie) |
| `/api/v1/auth/me` | GET | Bearer | none | `{user}` | none |

### Phase gate

Phase 1.1 chỉ "done" khi CẢ 5 gate pass:

| Gate | Tiêu chí | Cách verify |
|---|---|---|
| Static | ruff + mypy strict + 0 warning | `uv run ruff check . && uv run mypy app` |
| Unit | pytest pass + coverage ≥ 80% | `uv run pytest --cov=app --cov-fail-under=80` |
| **Postgres** | alembic upgrade/downgrade/upgrade trên PG thật pass | `docker exec ctsv-api uv run alembic upgrade head && ... downgrade -1 && ... upgrade head` |
| **Docker** | `make up --wait` + `make seed` + login/refresh/logout bằng curl | manual + `scripts/verify-env.sh` |
| **CI** | GitHub Actions api job pass với postgres service + integration test | xem `.github/workflows/ci.yml` |

PROGRESS.md ghi badge rõ:

```
✅ Static verified   — ruff + mypy clean
✅ Unit verified     — 49+ tests pass
⚠️ Postgres verified — chưa chạy trên PG thật
⚠️ Docker verified   — chưa start docker stack
⚠️ CI verified       — chưa add postgres service + integration job
```

## Consequences

### Tích cực

- Auth đủ chuẩn production (rotation + reuse detection + cookie).
- Config fail-closed ngăn leak secret mặc định.
- Health check thật → K8s rollout chính xác.
- CI phát hiện regression sớm.
- PROGRESS.md rõ ràng, không còn "verified" mơ hồ.

### Tiêu cực / Rủi ro

- ⚠️ Phase 1.1 mở rộng scope → estimate tăng ~30-40%. Cần Phase 1.2 (Runtime Verification) riêng để chạy integration test thật.
- ⚠️ pwdlib là dependency mới → cần pin version `pwdlib[argon2]>=0.2.0,<0.3`.
- ⚠️ Migration 0002 phải backward-compatible: password_hash cũ (bcrypt) vẫn verify được khi user login lần đầu → cần detect scheme + dual-verify OR force re-seed (chọn re-seed vì đang demo).
- ⚠️ Refresh cookie `Secure` ở production cần HTTPS → docs note rõ cho Phase deploy.
- ⚠️ Docker chưa có trên máy → mình KHÔNG tự `docker compose up`; user sẽ chạy thủ công sau khi apply phase này.

### Rollback

Nếu Phase 1.1 fail → giữ nguyên Phase 1 code, đổi main branch về commit trước. Refresh_sessions table chưa migrate thì zero-downtime.

## Ref

- Rule `.cursor/rules/06-security.mdc` — auth + cookie + audit.
- Rule `.cursor/rules/04-database-rag-ocr.mdc` — schema convention.
- Rule `.cursor/rules/05-testing.mdc` — coverage + integration.
- Rule `.cursor/rules/08-governance.mdc` — agent permission + idempotency.
- NIST 800-63B Session Management (reuse detection).
- OWASP Password Storage Cheat Sheet 2024 (argon2id recommendation).
- pwdlib docs: https://github.com/ya-mat/pwdlib