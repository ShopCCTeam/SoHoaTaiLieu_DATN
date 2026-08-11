"""document_chunks table with pgvector and full-text search.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-11
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        from pgvector.sqlalchemy import Vector
        from sqlalchemy.dialects.postgresql import TSVECTOR

        embedding_col = sa.Column("embedding", Vector(1024), nullable=False)
        tsv_col = sa.Column("fulltext_tsv", TSVECTOR, nullable=True)
    else:
        embedding_col = sa.Column("embedding", sa.JSON(), nullable=False)
        tsv_col = sa.Column("fulltext_tsv", sa.Text(), nullable=True)

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("block_ids", sa.JSON(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
        embedding_col,
        tsv_col,
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
            ["document_id"], ["documents.id"], ondelete="CASCADE"
        ),
    )

    op.create_index("ix_document_chunks_version_id", "document_chunks", ["version_id"])
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_page_number", "document_chunks", ["page_number"])
    op.create_index(
        "ix_document_chunks_version_index",
        "document_chunks",
        ["version_id", "chunk_index"],
    )
    op.create_index(
        "ix_document_chunks_document_page",
        "document_chunks",
        ["document_id", "page_number"],
    )

    if is_postgres:
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
            "ON document_chunks USING hnsw (embedding vector_cosine_ops);"
        )
        op.create_index(
            "ix_document_chunks_fulltext_tsv",
            "document_chunks",
            ["fulltext_tsv"],
            postgresql_using="gin",
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.drop_index("ix_document_chunks_fulltext_tsv", table_name="document_chunks")
        op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw;")

    op.drop_index("ix_document_chunks_document_page", table_name="document_chunks")
    op.drop_index("ix_document_chunks_version_index", table_name="document_chunks")
    op.drop_index("ix_document_chunks_page_number", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_version_id", table_name="document_chunks")
    op.drop_table("document_chunks")
