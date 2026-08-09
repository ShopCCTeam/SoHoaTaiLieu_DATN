"""Seed 3 demo users (admin/staff/student) — local dev only.

Chạy: `uv run python -m app.modules.auth.seed`

Idempotent: chạy nhiều lần không tạo duplicate (kiểm tra email trước).
"""
from __future__ import annotations

import asyncio
from typing import TypedDict

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.user import User
from app.modules.auth.security import hash_password


class DemoUserSpec(TypedDict):
    id: str
    email: str
    full_name: str
    role: str
    department: str | None


DEMO_PASSWORD = "Demo@2026"  # noqa: S105 — dev only, scoped to seed.

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


async def seed() -> None:
    session_factory = get_session_factory()
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
    print("\nDemo accounts ready. Password: Demo@2026")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
