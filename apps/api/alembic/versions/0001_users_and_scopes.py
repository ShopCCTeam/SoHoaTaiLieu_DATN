"""initial schema: users + document_scopes

Create Date: 2026-08-09
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---- users ----
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column(
            "role",
            sa.String(length=16),
            nullable=False,
            server_default="student",
        ),
        sa.Column("department", sa.String(length=120), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # ---- document_scopes ----
    op.create_table(
        "document_scopes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("code", name="uq_document_scopes_code"),
    )

    # ---- Seed 3 scopes (reference data) ----
    op.bulk_insert(
        sa.table(
            "document_scopes",
            sa.column("code", sa.String),
            sa.column("description", sa.String),
        ),
        [
            {"code": "PUBLIC", "description": "Công khai — Sinh viên xem được."},
            {
                "code": "STUDENT_AFFAIRS",
                "description": "Nội bộ Công tác Sinh viên — staff và student.",
            },
            {
                "code": "INTERNAL",
                "description": "Nội bộ Cán bộ — staff và admin.",
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("document_scopes")
    op.drop_table("users")