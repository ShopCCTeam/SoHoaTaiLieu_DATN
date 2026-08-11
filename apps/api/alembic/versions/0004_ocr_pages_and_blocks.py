"""ocr_pages and ocr_blocks tables for Phase C OCR Pipeline.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-11
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create ocr_pages table
    op.create_table(
        "ocr_pages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("image_key", sa.String(length=512), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="COMPLETED"
        ),
        sa.Column("block_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "has_warnings", sa.Boolean(), nullable=False, server_default="false"
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
        sa.ForeignKeyConstraint(
            ["version_id"], ["document_versions.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("version_id", "page_number", name="uq_ocr_pages_version_page"),
    )
    op.create_index("ix_ocr_pages_version_id", "ocr_pages", ["version_id"])

    # 2. Create ocr_blocks table
    op.create_table(
        "ocr_blocks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("page_id", sa.String(length=36), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("block_index", sa.Integer(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column(
            "requires_review",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "review_status",
            sa.String(length=32),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("edited_text", sa.Text(), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("reviewed_by", sa.String(length=36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "processing_time_ms",
            sa.Integer(),
            nullable=False,
            server_default="0",
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
        sa.ForeignKeyConstraint(
            ["version_id"], ["document_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["page_id"], ["ocr_pages.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"], ["users.id"], ondelete="SET NULL"
        ),
    )
    # Single column indexes
    op.create_index("ix_ocr_blocks_version_id", "ocr_blocks", ["version_id"])
    op.create_index("ix_ocr_blocks_page_id", "ocr_blocks", ["page_id"])
    op.create_index("ix_ocr_blocks_page_number", "ocr_blocks", ["page_number"])
    op.create_index("ix_ocr_blocks_requires_review", "ocr_blocks", ["requires_review"])
    op.create_index("ix_ocr_blocks_review_status", "ocr_blocks", ["review_status"])
    op.create_index("ix_ocr_blocks_job_id", "ocr_blocks", ["job_id"])

    # Composite index required by spec: ix_ocr_blocks_version_page on (version_id, page_number)
    op.create_index(
        "ix_ocr_blocks_version_page", "ocr_blocks", ["version_id", "page_number"]
    )
    op.create_index(
        "ix_ocr_blocks_version_page_index",
        "ocr_blocks",
        ["version_id", "page_number", "block_index"],
    )
    op.create_index(
        "ix_ocr_blocks_review_status_composite",
        "ocr_blocks",
        ["version_id", "requires_review", "review_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_ocr_blocks_review_status_composite", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_version_page_index", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_version_page", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_job_id", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_review_status", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_requires_review", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_page_number", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_page_id", table_name="ocr_blocks")
    op.drop_index("ix_ocr_blocks_version_id", table_name="ocr_blocks")
    op.drop_table("ocr_blocks")

    op.drop_index("ix_ocr_pages_version_id", table_name="ocr_pages")
    op.drop_table("ocr_pages")
