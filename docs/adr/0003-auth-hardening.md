# ADR-0003: Auth Hardening — Refresh Rotation + Argon2id + Runtime Postgres Verification

> Status: **Proposed** (2026-08-09)
> Author: AI agent + user review
> Review: user 2026-08-10 (v2 → v3) — **conditional approval**, cần 10 sửa đổi v3

## Context

Phase 1 đã implement `/auth/login` + `/auth/me` với:
- Bcrypt cost 12 (passlib).
- JWT access token (HS256, TTL 15 phút).
- 49 unit test pass với SQLite in-memory.
- Docker Compose chưa chạy trên máy local.

## Review history

### v2 corrections (2026-08-10) — ĐÃ ÁP DỤNG
1. `rotate_session` lookup `family_id` từ DB, không nhận từ client.
2. Family revocation commit trước raise HTTP error (không flush-then-raise).
3. Atomic rotation: `SELECT FOR UPDATE` hoặc conditional `UPDATE WHERE`.
4. Bỏ SQLite migration test.
5. Test reuse detection với assertion thật + pytest.raises.
6. Contract sync OpenAPI: refresh trả `{access_token, expires_in}`, logout trả `204`.
7. Argon2id dummy hash thay bcrypt dummy.
8. Mỗi commit build/test được; gộp password migration.
9. Commit ADR trước implementation.
10. Bổ sung cookie attrs, is_active check, audit events.

### v3 corrections (2026-08-10) — ĐANG ÁP DỤNG
1. **`found.user` không dùng được**: refresh service không load user; router/service load user rõ ràng trong transaction.
2. **Viết lại reuse persistence tests**: expired, concurrent, inactive user tests thật.
3. **Transaction ownership rõ ràng**: helper/service **không tự commit**; router/application layer commit một lần.
4. **OpenAPI trước implementation**: dùng existing `refreshCookie` scheme; thêm response models + AUTH error codes.
5. **Cookie tests kiểm tra Set-Cookie header**: httpx response headers, không chỉ `.cookies`.
6. **Origin-CSRF + structured audit events**: implement và test đầy đủ.
7. **Argon2id commit gồm**: uv.lock, seed fixtures; inactive login vẫn verify password; reset chỉ demo users.
8. **Chiến lược PostgreSQL types vs SQLite**: model tests dùng PG engine khi cần INET/UUID.
9. **CI chính xác**: pin oasdiff, đúng working directory, normalize `/api/v1`, coverage XML.
10. **Fail-closed staging+production**: dùng `URL.create`, `JSONResponse`, DB timeout config.

## Decision

### Phase split

| Phase | Nội dung | Gate |
|---|---|---|
| **Phase 1.1** — Auth Implementation | argon2id, refresh model, rotation service, auth routes, config fail-closed, health/ready, seed guard, CI | Static + Unit |
| **Phase 1.2** — Runtime Verification | docker stack, alembic PG thật, oasdiff CI, integration test | Postgres + Docker + CI |
| **Phase 1 Hoàn chỉnh** | 1.1 + 1.2 | Cả 5 gate |

### Quyết định kiến trúc

| # | Quyết định | Lý do |
|---|---|---|
| D1 | **Refresh token rotation**: opaque token + SHA-256 hash lưu DB. `family_id` lookup từ DB bằng `token_hash`. | Không client gửi `family_id` |
| D2 | **Cookie**: HttpOnly + SameSite=Lax + Secure(prod) + Path=/api/v1/auth + Max-Age. Clear dùng đúng path/attrs. | Rule 06 |
| D3 | **Reuse detection**: commit family revocation trước raise; thu hồi TOÀN BỘ family (NIST 800-63B). | Không rollback được |
| D4 | **Atomic rotation**: `SELECT FOR UPDATE` lock session + conditional `UPDATE WHERE id=:id AND revoked_at IS NULL`. | Chống concurrent refresh |
| D5 | **Transaction ownership**: service layer **không commit**. Helper trả raw objects; router/application gọi `session.commit()` một lần. | Sạch, predictable, dễ test |
| D6 | **User loading in transaction**: refresh endpoint load user rõ ràng bằng `session.get(User, user_id)`, không dùng lazy `found.user`. | SQLAlchemy async lazy load không an toàn |
| D7 | **Password hashing**: `bcrypt` → `pwdlib[argon2id]` (OWASP 2024). Valid argon2id dummy hash cố định. | Timing defense |
| D8 | **Demo data**: reset demo users bằng `seed --reset`; argon2id hashes mới. Inactive login vẫn verify password. | Không có production user |
| D9 | **Config fail-closed**: `APP_ENV ∈ {production, staging}` → reject default JWT secret, `localhost` CORS, `secure=false` cookie. Dùng `URL.create()` cho URL fields. | Defense-in-depth |
| D10 | **`/health/ready`**: `SELECT 1` thật tới Postgres; DB timeout 5s; trả 503 nếu fail. Dùng `JSONResponse` (không FastAPI default). | K8s probe |
| D11 | **Origin-CSRF**: refresh/logout kiểm tra `Origin` header; reject nếu missing/unexpected. | Rule 06 |
| D12 | **Structured audit events**: `structlog` JSON cho auth security events. audit_logs table pending — ghi rõ. | Rule 06 |
| D13 | **Logout idempotent**: token valid → revoke + clear; token invalid/missing → clear cookie + 204. | OAuth 2.0 BCP |
| D14 | **Refresh check user.is_active**: revoke family + trả 401 nếu user inactive. | Bảo vệ tài khoản bị khóa |
| D15 | **CI**: postgres service + alembic upgrade/downgrade + `--cov-fail-under=80` + oasdiff (pin version). Normalize OpenAPI base path `/api/v1`. | Rule 05 |
| D16 | **OpenAPI contract-first**: viết OpenAPI **trước** implementation; dùng existing `refreshCookie` scheme; response models + AUTH error codes. | Rule 03 |
| D17 | **Seed guard**: `APP_ENV ∈ {development, test}`; refuse ở production/staging. | Tránh seed nhầm prod |
| D18 | **PostgreSQL types in model tests**: test model dùng `POSTGRES_TEST_URL` khi cần INET/UUID; không test migration trên SQLite. | Migration dùng PG-specific types |

### PostgreSQL types strategy

```
Model tests (SQLAlchemy ORM):
  ├─ Unit tests (SQLite): test table name, columns, relationships — không cần INET/UUID
  └─ Integration tests (Postgres): test INET, UUID, pgcrypto — chạy trong CI

Migration tests:
  ├─ Alembic revision chain: walk script (no DB needed)
  └─ Apply/rollback: trên PG thật trong CI, KHÔNG trên SQLite
```

### Out of scope

- ❌ `/documents` GET (Phase 2).
- ❌ Celery + MinIO (Phase 3).
- ❌ OCR (Phase 4).
- ❌ RAG/pgvector (Phase 5).
- ❌ Persistent `audit_logs` table (dùng structured security log; pending).

### Schema: `refresh_sessions`

```sql
CREATE TABLE refresh_sessions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  family_id       UUID NOT NULL,
  token_hash      VARCHAR(64) NOT NULL UNIQUE,
  user_agent      VARCHAR(512) NULL,
  ip_address      INET NULL,
  issued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at      TIMESTAMPTZ NOT NULL,
  revoked_at      TIMESTAMPTZ NULL,
  replaced_by_id  UUID NULL REFERENCES refresh_sessions(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_refresh_sessions_user_id    ON refresh_sessions(user_id);
CREATE INDEX ix_refresh_sessions_family_id  ON refresh_sessions(family_id);
CREATE INDEX ix_refresh_sessions_token_hash ON refresh_sessions(token_hash);
CREATE INDEX ix_refresh_sessions_expires_at ON refresh_sessions(expires_at);
CREATE INDEX ix_refresh_sessions_revoked_at ON refresh_sessions(revoked_at);
```

### API contract (source: OpenAPI — viết TRƯỚC implementation)

**Response models:**

```yaml
RefreshResponse:
  type: object
  required: [access_token, expires_in]
  properties:
    access_token: {type: string, description: "JWT access token mới (HS256)"}
    expires_in: {type: integer, description: "TTL access token (seconds)", example: 900}

LogoutResponse:
  type: object
  description: "204 No Content — luôn trả khi request hợp lệ"
  required: []
  properties: {}

AuthError:
  type: object
  required: [code, detail]
  properties:
    code: {type: string, enum: [
      AUTH_INVALID_CREDENTIALS,
      AUTH_USER_INACTIVE,
      AUTH_REFRESH_INVALID,
      AUTH_REFRESH_EXPIRED,
      AUTH_REFRESH_REUSE_DETECTED,
      AUTH_CSRF_MISSING_ORIGIN,
    ]}
    detail: {type: string}
```

**Endpoints:**

| Endpoint | Verb | Auth | Body | Response | Cookie |
|---|---|---|---|---|---|
| `/api/v1/auth/login` | POST | none | `{email, password}` | `200 {access_token, expires_in, user}` | `rt=<opaque>; HttpOnly; SameSite=Lax; Secure(prod); Path=/api/v1/auth; Max-Age=604800` |
| `/api/v1/auth/refresh` | POST | `refreshCookie` | none | `200 {access_token, expires_in}` | `rt=<new-opaque>` |
| `/api/v1/auth/logout` | POST | `refreshCookie` | none | `204 No Content` | `rt=; Max-Age=0` |
| `/api/v1/auth/me` | GET | `bearerAuth` | none | `200 {user}` | none |

**AUTH error codes:**

| Code | HTTP | Khi nào |
|---|---|---|
| `AUTH_INVALID_CREDENTIALS` | 401 | Login: email/password sai |
| `AUTH_USER_INACTIVE` | 401 | Login/refresh: user bị disable |
| `AUTH_REFRESH_INVALID` | 401 | Refresh: token không tồn tại |
| `AUTH_REFRESH_EXPIRED` | 401 | Refresh: token đã hết hạn |
| `AUTH_REFRESH_REUSE_DETECTED` | 401 | Refresh: token đã bị dùng lại (family revoked) |
| `AUTH_CSRF_MISSING_ORIGIN` | 403 | Refresh/logout: Origin header missing/unexpected |

### Security log events

```python
audit_log("auth.login.success", user_id=user.id, ip=ip, user_agent=ua)
audit_log("auth.login.failed", email_hash=sha256(email), reason=reason, ip=ip)
audit_log("auth.refresh.rotated", user_id=user_id, family_id=family_id)
audit_log("auth.refresh.reuse_detected", family_id=family_id, ip=ip)  # ERROR level
audit_log("auth.refresh.expired", family_id=family_id)
audit_log("auth.refresh.inactive_user", user_id=user_id)
audit_log("auth.logout", user_id=user_id)
audit_log("auth.session.family_revoked", family_id=family_id, reason=reason)
```

### Verify gate

Phase 1.1 (Static + Unit):

| Gate | Command |
|---|---|
| Static | `uv run ruff check . && uv run ruff format --check . && uv run mypy app` |
| Unit | `uv run pytest --cov=app --cov-fail-under=80` |

Phase 1.2 (Runtime):

| Gate | Command |
|---|---|
| Postgres | Alembic upgrade/downgrade/upgrade trên PG thật |
| Docker | `make up --wait && make seed && curl login/refresh/logout` |
| CI | GitHub Actions api job pass |

## Consequences

### Tích cực
- Transaction ownership rõ ràng: helper/service không commit, router commit một lần.
- Contract-first: OpenAPI viết trước, implementation theo contract.
- Audit events đầy đủ, CSRF protection có test.
- CI chính xác, coverage không bị sai.

### Tiêu cực / Rủi ro
- ⚠️ Demo users cần `seed --reset` sau khi chuyển argon2id.
- ⚠️ Docker chưa có → Phase 1.2 gate user chạy thủ công.
- ⚠️ Audit dùng structured log; audit_logs table còn pending.

### Rollback

Nếu fail → `git revert` hoặc forward-fix. Không `git reset --hard`.

## Ref

- Rule 06 (auth + cookie + audit), Rule 04 (schema), Rule 05 (coverage), Rule 08 (agent).
- NIST 800-63B, OWASP 2024, OAuth 2.0 BCP.
- pwdlib: https://github.com/ya-mat/pwdlib