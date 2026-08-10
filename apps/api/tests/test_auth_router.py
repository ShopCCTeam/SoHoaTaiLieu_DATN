"""Tests cho /auth/login + /auth/refresh + /auth/logout + /auth/me endpoints.

Test theo ADR-0003 v3:
- Cookie Set-Cookie headers (httpx response.headers).
- Origin-CSRF check.
- Refresh token reuse detection.
- Logout idempotent.
- P0 hardening: audit log không được chứa refresh_token plaintext,
  revoke phải ghi DB (không chỉ status code).
"""
from __future__ import annotations

import asyncio
from datetime import UTC

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.session import get_session
from app.models.refresh_session import RefreshSession
from app.models.user import User


def _extract_rt_cookie(cookie_header: str) -> str | None:
    """Extract `rt=<token>` từ Set-Cookie header string.

    `httpx.Response.headers.get("set-cookie", "")` trả về string cookie đầu
    tiên — nhưng để chắc chắn (test mock có thể trả về nhiều cookie), scan
    mọi `;`-separated part.
    """
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        if "rt=" in part.lower():
            return part.split("rt=", 1)[1].strip()
    return None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_refresh_cookie(cookies: dict[str, str]) -> str | None:
    """Extract rt cookie value from httpx cookies."""
    return cookies.get("rt")


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success_sets_refresh_cookie(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    """Login returns 200 + sets HttpOnly refresh cookie."""
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert body["data"]["user"]["email"] == "admin@example.edu.vn"

    # Cookie phải được set
    set_cookie = response.headers.get("set-cookie", "")
    assert "rt=" in set_cookie.lower()
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "WrongPass!"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.edu.vn", "password": "Demo@2026"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_inactive_user_returns_401(
    db_session_factory: async_sessionmaker,
) -> None:
    from app.main import create_app
    from app.modules.auth.security import hash_password

    async with db_session_factory() as session:
        user = User(
            id="usr_inactive",
            email="inactive@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="Inactive User",
            role="staff",
            is_active=False,
        )
        session.add(user)
        await session.commit()

    app = create_app()

    async def _override():
        async with db_session_factory() as s:
            yield s
            await s.commit()

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.edu.vn", "password": "Demo@2026"},
        )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"


# ---------------------------------------------------------------------------
# /me tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_me_with_valid_token_returns_user(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    token = login.json()["data"]["access_token"]

    response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["user"]["email"] == "admin@example.edu.vn"


@pytest.mark.asyncio
async def test_me_without_token_returns_401(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_MISSING_TOKEN"


@pytest.mark.asyncio
async def test_me_with_invalid_token_returns_401(api_client: AsyncClient) -> None:
    response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.asyncio
async def test_me_with_expired_token_returns_401(
    seeded_user: User,
) -> None:
    from app.main import create_app
    from app.modules.auth.security import create_access_token

    app = create_app()
    expired_token = create_access_token(
        subject=seeded_user.id,
        role=seeded_user.role,
        ttl_seconds=1,
    )
    await asyncio.sleep(2)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_EXPIRED"


# ---------------------------------------------------------------------------
# Refresh tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_returns_new_access_token(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    # Login first
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )

    # Extract cookie
    cookie_header = login.headers.get("set-cookie", "")
    rt_cookie = _extract_rt_cookie(cookie_header)

    assert rt_cookie is not None, f"No rt cookie in: {cookie_header}"

    # Refresh
    response = await api_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:3000",
            "Cookie": f"rt={rt_cookie}",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "access_token" in body["data"]
    # Access token có thể giống vì cùng TTL và timing; key là rotation đã xảy ra.
    # Verify rotation qua test khác (reuse detection).


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REFRESH_INVALID"


@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_401(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:3000",
            "Cookie": "rt=invalid_token_not_in_db",
        },
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REFRESH_INVALID"


@pytest.mark.asyncio
async def test_refresh_rotation_revokes_old_token(
    api_client: AsyncClient,
    seeded_user: User,
    db_session_factory: async_sessionmaker,
) -> None:
    """P0 bảo vệ: rotation phải revoke toàn bộ family trong DB.

    Test cũ chỉ check status code — pass ngay cả khi fix P0-2 (revert
    family_id về uuid4) bị bỏ. Bây giờ assert session.active_count theo
    family phải về 0 sau reuse detected.
    """
    # Login
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    rt_token = _extract_rt_cookie(login.headers.get("set-cookie", ""))
    assert rt_token is not None, f"No rt cookie in headers: {login.headers.get('set-cookie', '')}"

    # Refresh lần 1 → nhận token mới
    r1 = await api_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:3000",
            "Cookie": f"rt={rt_token}",
        },
    )
    assert r1.status_code == 200
    r1_cookie = r1.headers.get("set-cookie", "")
    rt_token_2 = None
    for part in r1_cookie.split(";"):
        if "rt=" in part.lower():
            rt_token_2 = part.split("rt=", 1)[1].strip().split(";")[0]
            break
    assert rt_token_2 is not None
    assert rt_token_2 != rt_token

    # Dùng token cũ lần 2 → reuse detected → 401
    r2 = await api_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:3000",
            "Cookie": f"rt={rt_token}",
        },
    )
    assert r2.status_code == 401
    assert r2.json()["code"] == "AUTH_REFRESH_REUSE_DETECTED"

    # P0 bảo vệ: sau reuse, toàn bộ session trong family phải revoked.
    # Lấy family_id qua bất kỳ session nào còn trong DB (token_hash của
    # rt_token_2 chưa bị rotate nên revoked_at IS NULL — tìm family từ nó).
    from app.modules.auth.security import hash_token

    new_token_hash = hash_token(rt_token_2)
    async with db_session_factory() as session:
        row = await session.execute(
            select(RefreshSession).where(
                RefreshSession.token_hash == new_token_hash,
            )
        )
        rs = row.scalar_one()
        family_id = rs.family_id

        # Sau reuse detected, mọi session trong family phải có revoked_at
        active_count = await session.execute(
            select(func.count())
            .select_from(RefreshSession)
            .where(
                RefreshSession.family_id == family_id,
                RefreshSession.revoked_at.is_(None),
            )
        )
    assert active_count.scalar_one() == 0, (
        f"Reuse detected nhưng family={family_id} còn session active — "
        "fix P0-2 (revoke_family) đã bị revert"
    )


# ---------------------------------------------------------------------------
# CSRF tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_missing_origin_returns_200(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    """Không có Origin header → cho qua (curl, Next.js route handler không gửi Origin)."""
    # Login
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    cookie_header = login.headers.get("set-cookie", "")
    rt_token = _extract_rt_cookie(cookie_header)
    assert rt_token is not None

    # Refresh WITHOUT Origin header → 200 (same-site, no CSRF risk)
    response = await api_client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"rt={rt_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]


@pytest.mark.asyncio
async def test_refresh_unexpected_origin_returns_403(
    api_client: AsyncClient,
    seeded_user: User,
) -> None:
    """Origin không trong CORS list → 403 AUTH_CSRF_ORIGIN_REJECTED."""
    # Login
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    cookie_header = login.headers.get("set-cookie", "")
    rt_token = _extract_rt_cookie(cookie_header)
    assert rt_token is not None

    # Refresh với Origin không trong CORS list → 403
    response = await api_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "https://evil.example.com",
            "Cookie": f"rt={rt_token}",
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_CSRF_ORIGIN_REJECTED"


# ---------------------------------------------------------------------------
# Audit log safety — P0 hardening
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_does_not_leak_refresh_token(
    api_client: AsyncClient,
    seeded_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P0: refresh token plaintext KHÔNG được xuất hiện trong audit log.

    Trước P0 fix: router hack `family_id=str(rotation.refresh_token[:16])`
    → log chứa 16 ký tự đầu của refresh token (LEAK SECRET).

    Bảo vệ 4 lớp (đã bị bypass 2 lần trước đây):
    1. Negative control: assert captured có ≥1 entry.
       `structlog.testing.capture_logs()` KHÔNG hoạt động khi app đã
       `structlog.configure(..., JSONRenderer(), cache_logger_on_first_use=True)`
       (production setup) — test cũ capture rỗng → assertions KHÔNG chạy → xanh
       giả. Phải monkeypatch `_audit._logger.info` (BoundLogger thật) để
       intercept call.
    2. Parse token MỚI từ response.headers["set-cookie"] → assert
       new_token != rt_token (rotation thật sự xảy ra).
    3. Forbidden list: rt_token, new_token, prefix [:16]/[:8]/[8:24] của CẢ HAI,
       hash_token() của CẢ HAI. Hai token là hai secrets độc lập — bug cũ leak
       `rotation.refresh_token[:16]` = new_token, không liên quan rt_token.
    4. Join toàn bộ captured thành 1 string → assert từng giá trị forbidden
       KHÔNG xuất hiện. Tránh false negative khi token bị split across nhiều
       event/field.
    """
    from app.modules.auth import audit as audit_module
    from app.modules.auth.security import hash_token

    # Intercept BoundLogger thật của `_audit` — structlog.testing.capture_logs()
    # không hoạt động sau configure(JSONRenderer, cache_logger_on_first_use=True).
    captured: list[tuple[str, dict[str, object]]] = []

    def _capture(event: str, *args: object, **kw: object) -> object:
        captured.append((event, dict(kw)))
        return None

    monkeypatch.setattr(audit_module._audit, "info", _capture)

    # Login first
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    rt_token = _extract_rt_cookie(login.headers.get("set-cookie", ""))
    assert rt_token is not None, f"No rt cookie in headers: {login.headers.get('set-cookie', '')}"
    assert len(rt_token) >= 24, f"rt_token ngắn bất thường: {rt_token!r}"

    # Refresh — audit_log._audit.info bị intercept
    response = await api_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:3000",
            "Cookie": f"rt={rt_token}",
        },
    )
    assert response.status_code == 200, response.text

    # (1) Negative control — captured phải có event rotated.
    # Nếu `captured == []` → monkeypatch không chạm đúng logger → assertion
    # dưới trở thành xanh giả (đây là vấn đề của test cũ với capture_logs).
    events = [e[0] for e in captured]
    assert "auth.refresh.rotated" in events, (
        f"audit_log._audit.info không bị intercept — capture bị broken. "
        f"captured events: {events}"
    )

    # (2) Parse token MỚI từ Set-Cookie response — rotation thật sự xảy ra.
    new_token = _extract_rt_cookie(response.headers.get("set-cookie", ""))
    assert new_token is not None, (
        f"refresh response thiếu rt cookie: {response.headers.get('set-cookie', '')!r}"
    )
    assert new_token != rt_token, (
        "Rotation không xảy ra — test không có ý nghĩa (test cũ leak secret "
        "chỉ chạy khi rotation xảy ra)."
    )

    # (3) Forbidden list — cả token cũ + token mới + các prefix/substring + hash.
    # Bug cũ leak `rotation.refresh_token[:16]` = 16 ký tự đầu của new_token,
    # không liên quan rt_token → phải kiểm cả hai.
    forbidden = {
        "rt_token": rt_token,
        "new_token": new_token,
        "rt_token[:16]": rt_token[:16],
        "rt_token[:8]": rt_token[:8],
        "rt_token[8:24]": rt_token[8:24],
        "new_token[:16]": new_token[:16],
        "new_token[:8]": new_token[:8],
        "new_token[8:24]": new_token[8:24],
        "rt_token_hash": hash_token(rt_token),
        "new_token_hash": hash_token(new_token),
    }
    forbidden = {k: v for k, v in forbidden.items() if v}

    # (4) Join toàn bộ captured thành 1 string — bắt mọi leak dù split field nào.
    captured_str = str(captured)
    for label, value in forbidden.items():
        assert value not in captured_str, (
            f"Audit log leak [{label}]={value!r} xuất hiện trong captured logs. "
            f"Đây là secret leak — refresh token (hoặc hash/prefix) bị ghi vào log."
        )


# ---------------------------------------------------------------------------
# Logout tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_revokes_token_and_clears_cookie(
    api_client: AsyncClient,
    seeded_user: User,
    db_session_factory: async_sessionmaker,
) -> None:
    # Login
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.edu.vn", "password": "Demo@2026"},
    )
    cookie_header = login.headers.get("set-cookie", "")
    rt_token = _extract_rt_cookie(cookie_header)
    assert rt_token is not None

    # Logout
    response = await api_client.post(
        "/api/v1/auth/logout",
        headers={
            "Origin": "http://localhost:3000",
            "Cookie": f"rt={rt_token}",
        },
    )
    assert response.status_code == 204

    # Cookie phải được clear
    clear_cookie = response.headers.get("set-cookie", "")
    assert "rt=" in clear_cookie.lower()
    assert "max-age=0" in clear_cookie.lower()

    # P0 bảo vệ: session trong DB phải có revoked_at IS NOT NULL.
    from app.modules.auth.security import hash_token

    rt_token_hash = hash_token(rt_token)
    async with db_session_factory() as session:
        row = await session.execute(
            select(RefreshSession).where(
                RefreshSession.token_hash == rt_token_hash,
            )
        )
        rs = row.scalar_one()
        assert rs.revoked_at is not None, (
            "Logout trả 204 nhưng session chưa revoke trong DB — "
            "revoke_refresh_token đã bị bypass"
        )


@pytest.mark.asyncio
async def test_logout_idempotent_no_token(api_client: AsyncClient) -> None:
    """Logout không có token → still 204 (idempotent)."""
    response = await api_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_logout_csrf_requires_origin(api_client: AsyncClient) -> None:
    """Logout không có Origin → cho qua (idempotent, 204)."""
    response = await api_client.post("/api/v1/auth/logout")
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_inactive_user_returns_401_no_session_created(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    """P0 bảo vệ: inactive user ở refresh → 401 + KHÔNG tạo session mới.

    Test cũ viết sai: user inactive → 401 ngay ở login → không hề gọi
    /auth/refresh. Fix: login trước (active) → set is_active=False → /refresh.
    """
    from app.modules.auth.security import hash_password

    # Tạo user ACTIVE trước (login phải thành công)
    async with db_session_factory() as session:
        user = User(
            id="usr_inactive_refresh",
            email="inactive_refresh@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="Inactive Refresh Test",
            role="staff",
            is_active=True,  # ACTIVE để login được
        )
        session.add(user)
        await session.commit()

    # Login lấy cookie
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "inactive_refresh@example.edu.vn", "password": "Demo@2026"},
    )
    assert login.status_code == 200, login.text
    cookie_header = login.headers.get("set-cookie", "")
    rt_token = _extract_rt_cookie(cookie_header)
    assert rt_token is not None
    assert rt_token is not None

    # Set user inactive SAU khi login
    async with db_session_factory() as session:
        u = await session.get(User, "usr_inactive_refresh")
        assert u is not None
        u.is_active = False
        await session.commit()

    # Đếm session SAU login nhưng TRƯỚC refresh — baseline phải là 1
    # (1 session từ login vừa rồi).
    async with db_session_factory() as session:
        before = await session.execute(
            select(func.count())
            .select_from(RefreshSession)
            .where(RefreshSession.user_id == "usr_inactive_refresh")
        )
    before_count = before.scalar_one()
    assert before_count == 1, (
        f"Login phải tạo 1 session, hiện có {before_count}"
    )

    # Refresh → 401 AUTH_REFRESH_INVALID (inactive user ở refresh)
    response = await api_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:3000",
            "Cookie": f"rt={rt_token}",
        },
    )
    assert response.status_code == 401, response.text
    assert response.json()["code"] == "AUTH_REFRESH_INVALID"

    # Số session KHÔNG tăng (rotation bị từ chối trước khi tạo session mới)
    async with db_session_factory() as session:
        after = await session.execute(
            select(func.count())
            .select_from(RefreshSession)
            .where(RefreshSession.user_id == "usr_inactive_refresh")
        )
    after_count = after.scalar_one()
    assert after_count == before_count, (
        f"Refresh trên inactive user đã tạo {after_count - before_count} "
        "session mới — rotation phải abort trước session.add"
    )


@pytest.mark.asyncio
async def test_refresh_expired_token_returns_401_expired_code(
    db_session_factory: async_sessionmaker,
) -> None:
    """Refresh với expired token → 401 AUTH_REFRESH_EXPIRED."""
    import uuid as uuid_module

    from app.main import create_app
    from app.modules.auth.security import hash_password

    async with db_session_factory() as session:
        user = User(
            id="usr_expired_refresh",
            email="expired_refresh@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="Expired Refresh Test",
            role="student",
            is_active=True,
        )
        session.add(user)
        await session.commit()

    app = create_app()

    async def _override():
        async with db_session_factory() as s:
            yield s
            await s.commit()

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Tạo session đã hết hạn trực tiếp
        from datetime import datetime, timedelta

        from app.modules.auth.refresh_service import _generate_opaque_token
        from app.modules.auth.security import hash_token

        expired_token = _generate_opaque_token()
        from app.models.refresh_session import RefreshSession

        async with db_session_factory() as session:
            rs = RefreshSession(
                id=uuid_module.uuid4(),  # UUID object, not string
                user_id="usr_expired_refresh",
                family_id=uuid_module.uuid4(),
                token_hash=hash_token(expired_token),
                issued_at=datetime.now(UTC) - timedelta(seconds=200),
                expires_at=datetime.now(UTC) - timedelta(seconds=100),  # đã hết hạn
            )
            session.add(rs)
            await session.commit()

        # Refresh với token hết hạn
        response = await client.post(
            "/api/v1/auth/refresh",
            headers={
                "Origin": "http://localhost:3000",
                "Cookie": f"rt={expired_token}",
            },
        )
        assert response.status_code == 401
        assert response.json()["code"] == "AUTH_REFRESH_EXPIRED"


# ---------------------------------------------------------------------------
# Login sets refresh session in DB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_creates_refresh_session_in_db(
    db_session_factory: async_sessionmaker,
) -> None:
    from sqlalchemy import select

    from app.main import create_app
    from app.modules.auth.security import hash_password

    async with db_session_factory() as session:
        user = User(
            id="usr_login_session",
            email="session_test@example.edu.vn",
            password_hash=hash_password("Demo@2026"),
            full_name="Session Test",
            role="staff",
            is_active=True,
        )
        session.add(user)
        await session.commit()

    app = create_app()

    async def _override():
        async with db_session_factory() as s:
            yield s
            await s.commit()

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "session_test@example.edu.vn", "password": "Demo@2026"},
        )
    assert login.status_code == 200

    # Verify refresh session was created
    async with db_session_factory() as session:
        stmt = select(RefreshSession).where(
            RefreshSession.user_id == "usr_login_session"
        )
        sessions = (await session.execute(stmt)).scalars().all()
        assert len(sessions) == 1
        assert sessions[0].user_id == "usr_login_session"
        assert sessions[0].revoked_at is None
        assert len(sessions[0].token_hash) == 64  # SHA-256 hex


# ---------------------------------------------------------------------------
# revoke_all_user_sessions — Phase 5 P0 coverage
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_revoke_all_user_sessions_returns_count(
    db_session_factory: async_sessionmaker,
) -> None:
    """Service `revoke_all_user_sessions` trả về rowcount đúng.

    Phase 5 audit: hàm này trước đó có 0 test, coverage 81% ăn 1 dòng
    trivial. Cover edge cases: 0 session, N active sessions.
    """
    from app.modules.auth.refresh_service import revoke_all_user_sessions

    # Case 1: user không có session → return 0
    async with db_session_factory() as session:
        count = await revoke_all_user_sessions(
            session, "usr_no_sessions", reason="password_change"
        )
        await session.commit()
    assert count == 0

    # Case 2: tạo 3 session ACTIVE cho user → revoke_all → return 3
    import uuid as uuid_module
    from datetime import UTC, datetime, timedelta

    from app.modules.auth.security import hash_token

    user_id = "usr_revoke_all"
    async with db_session_factory() as session:
        u = User(
            id=user_id,
            email="revoke_all@example.edu.vn",
            password_hash=hash_token("ignored"),  # dummy
            full_name="Revoke All",
            role="staff",
            is_active=True,
        )
        # Override hash_password to avoid bcrypt cost in test
        from app.modules.auth.security import hash_password

        u.password_hash = hash_password("Demo@2026")
        session.add(u)
        await session.commit()

    now = datetime.now(UTC)
    async with db_session_factory() as session:
        for i in range(3):
            rs = RefreshSession(
                id=uuid_module.uuid4(),
                user_id=user_id,
                family_id=uuid_module.uuid4(),
                token_hash=f"{i:x}" * 64,  # unique hash per session
                issued_at=now,
                expires_at=now + timedelta(seconds=3600),
            )
            session.add(rs)
        await session.commit()

    async with db_session_factory() as session:
        count = await revoke_all_user_sessions(
            session, user_id, reason="password_change"
        )
        await session.commit()
    assert count == 3, f"expected 3 revoked, got {count}"

    # Gọi lần 2 → tất cả đã revoked → return 0
    async with db_session_factory() as session:
        count_2 = await revoke_all_user_sessions(
            session, user_id, reason="password_change"
        )
        await session.commit()
    assert count_2 == 0, f"lần 2 phải return 0, got {count_2}"
