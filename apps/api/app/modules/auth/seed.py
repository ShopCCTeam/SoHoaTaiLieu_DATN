"""Seed 3 demo users (admin/staff/student) — local dev only.

Chạy:
  uv run python -m app.modules.auth.seed          # seed bình thường
  uv run python -m app.modules.auth.seed --reset   # xoá + seed lại

Idempotent: chạy không có --reset nhiều lần không tạo duplicate.
Email từ hằng số (không hardcode @ctsv.edu.vn).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import TypedDict

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.user import User
from app.modules.auth.security import hash_password

# ---- Constants ----
DEMO_PASSWORD = "Demo@2026"  # noqa: S105 — dev only, scoped to seed.

DEMO_EMAILS = (
    "admin@example.edu.vn",
    "staff@example.edu.vn",
    "student@example.edu.vn",
)


class DemoUserSpec(TypedDict):
    id: str
    email: str
    full_name: str
    role: str
    department: str | None


DEMO_USERS: list[DemoUserSpec] = [
    {
        "id": "usr_admin_demo",
        "email": "admin@example.edu.vn",
        "full_name": "Quản Trị Viên",
        "role": "admin",
        "department": "Phòng CTSV",
    },
    {
        "id": "usr_staff_demo",
        "email": "staff@example.edu.vn",
        "full_name": "Cán Bộ CTSV",
        "role": "staff",
        "department": "Phòng CTSV",
    },
    {
        "id": "usr_student_demo",
        "email": "student@example.edu.vn",
        "full_name": "Nguyễn Văn A",
        "role": "student",
        "department": None,
    },
]


async def _reset() -> None:
    """Xoá tất cả demo users, reset auto-increment."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        for email in DEMO_EMAILS:
            stmt = select(User).where(User.email == email)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                await session.delete(existing)
                print(f"[del] {email}")
        await session.commit()


async def seed(*, reset: bool = False) -> None:
    """Tạo 3 demo users.

    Args:
        reset: Nếu True, xoá users hiện có trước khi seed.
    """
    session_factory = get_session_factory()

    if reset:
        await _reset()

    async with session_factory() as session:
        for spec in DEMO_USERS:
            stmt = select(User).where(User.email == spec["email"])
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                print(f"[skip] {spec['email']} already exists")
                continue
            user = User(
                id=spec["id"],
                email=spec["email"],
                password_hash=hash_password(DEMO_PASSWORD),
                full_name=spec["full_name"],
                role=spec["role"],
                department=spec["department"],
                is_active=True,
            )
            session.add(user)
            print(f"[create] {spec['email']} ({spec['role']})")
        await session.commit()
    print(f"\nDemo accounts ready. Password: {DEMO_PASSWORD}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo users.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Xoá demo users hiện có trước khi seed lại.",
    )
    args = parser.parse_args(sys.argv[1:] if len(sys.argv) > 1 else [])
    asyncio.run(seed(reset=args.reset))


if __name__ == "__main__":
    main()
