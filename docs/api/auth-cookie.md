# Auth — Cookie + Refresh Token Rotation

> File này là spec cho FE + BE phối hợp trong auth flow. Đã chốt ở review P0.

## Tóm tắt

| Item | Lưu trữ | Lý do |
|---|---|---|
| **Access token** | Memory (FE state) hoặc sessionStorage mã hoá | Rủi ro XSS thấp hơn localStorage; lifetime ngắn (15 phút). |
| **Refresh token** | `HttpOnly` cookie `rt` (server set) | KHÔNG thể đọc từ JavaScript → chống XSS đánh cắp. |
| **Cookie path** | `/api/v1/auth` | Chỉ gửi kèm request tới auth endpoints. |
| **Cookie scope** | SameSite=Lax (HTTP), Strict (HTTPS) | Chống CSRF cho cross-site form POST. |

## Cookie attribute (bắt buộc)

```
Set-Cookie: rt=<opaque_token>;
  HttpOnly;
  Secure;                  # bắt buộc ở production (HTTPS)
  SameSite=Lax;            # Strict nếu không cần cross-origin OAuth
  Path=/api/v1/auth;       # chỉ gửi cho auth endpoints
  Max-Age=604800;          # 7 ngày
```

## Token format

- **Access token**: JWT HS256, chứa `sub` (user_id), `session_id`, `role`, `iat`, `exp` (15 phút).
- **Refresh token**: opaque random 32 bytes, base64url encoded. KHÔNG phải JWT.
  - Lưu ở server: `refresh_tokens` table với `id`, `session_id`, `token_hash`, `expires_at`, `revoked_at`, `replaced_by_id`, `user_agent`, `ip`.

## Session & rotation

Mỗi login tạo 1 `session_id` (UUID v7). Mọi refresh token rotate cùng session_id.

```
session_id = uuid7()
   ├─ refresh_token_v1 (active)  → used → issue v2
   ├─ refresh_token_v2 (active)  → used → issue v3
   └─ ...
```

### Reuse detection

Nếu BE nhận refresh token đã bị `revoked_at` NOT NULL:
1. **Không** cấp token mới.
2. **Revoke toàn bộ session** (`session_id` đó).
3. Log audit `auth.refresh_reuse_detected`.
4. Trả 401 + clear cookie `rt`.

## Endpoints contract (xem `docs/api/openapi.yaml`)

| Endpoint | Body / Cookie | Response | Cookie update |
|---|---|---|---|
| `POST /auth/login` | body `{email, password}` | `{access_token, expires_in, user}` | Set `rt` mới |
| `POST /auth/refresh` | cookie `rt` | `{access_token, expires_in}` | Rotate `rt` |
| `POST /auth/logout` | cookie `rt` | 204 | Clear `rt` (Max-Age=0) |
| `GET /auth/me` | header `Authorization: Bearer` | `{user}` | — |

## FE flow

```
1. Login → nhận access_token + user.
   Lưu access_token vào Zustand memory (KHÔNG persist localStorage).
   Cookie `rt` tự browser quản lý.

2. Mọi request gắn Authorization: Bearer access_token.
   TanStack Query có thể wrap vào interceptor.

3. Khi access_token hết hạn (response 401):
   a. Gọi POST /auth/refresh (cookie tự gửi).
   b. Nếu 200 → cập nhật access_token mới, retry request cũ.
   c. Nếu 401 → clear state, redirect /login.

4. Logout:
   a. POST /auth/logout (cookie tự gửi).
   b. Clear access_token + user state.
   c. Redirect /login.
```

## Lý do không lưu refresh token trong body

- **XSS**: Nếu attacker inject script, có thể đọc localStorage → đánh cắp refresh → impersonate 7 ngày.
- **HttpOnly cookie** chống XSS vì JavaScript không đọc được.
- **Logout invalidates token** ngay cả khi attacker có token (qua session_id revoke).

## Audit

Mọi auth event ghi vào `audit_logs`:
- `auth.login` (success/fail) — ghi `user_id`, IP, user agent.
- `auth.refresh` — ghi `user_id`, `session_id`.
- `auth.logout` — ghi `user_id`.
- `auth.refresh_reuse_detected` — ghi `user_id`, IP, token family (revoke all).

## Implementation note cho BE

```python
# apps/api/app/core/security.py
import secrets
from datetime import datetime, timezone, timedelta

REFRESH_TOKEN_BYTES = 32
REFRESH_TOKEN_TTL = timedelta(days=7)
ACCESS_TOKEN_TTL = timedelta(minutes=15)

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)

def hash_refresh_token(token: str) -> str:
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()
```

Cookie attributes:

```python
# apps/api/app/api/v1/auth/cookies.py
from fastapi import Response

REFRESH_COOKIE_NAME = "rt"
REFRESH_COOKIE_PATH = "/api/v1/auth"

def set_refresh_cookie(response: Response, token: str, secure: bool) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",  # Strict nếu không có OAuth cross-site
        path=REFRESH_COOKIE_PATH,
        max_age=int(REFRESH_TOKEN_TTL.total_seconds()),
    )

def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
    )
```