"""Shared, database-side metadata filters for documents and hybrid retrieval."""

from __future__ import annotations

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.document import Document


def normalize_tags(tags: list[str] | None) -> list[str]:
    """Return unique, non-empty tags normalized for case-insensitive exact matching."""
    if not tags:
        return []

    normalized_tags: list[str] = []
    seen_tags: set[str] = set()
    for tag in tags:
        normalized_tag = tag.strip().lower()
        if normalized_tag and normalized_tag not in seen_tags:
            normalized_tags.append(normalized_tag)
            seen_tags.add(normalized_tag)
    return normalized_tags


def _tag_exists_condition(tag: str, is_postgres: bool) -> ColumnElement[bool]:
    """Build a dialect-specific EXISTS condition for one exact JSON array tag."""
    if is_postgres:
        tag_rows = func.json_array_elements_text(Document.tags).table_valued("value").alias("tag")
    else:
        tag_rows = func.json_each(Document.tags).table_valued("value").alias("tag")

    return select(1).select_from(tag_rows).where(func.lower(tag_rows.c.value) == tag).exists()


def build_document_metadata_conditions(
    *,
    keyword: str | None,
    tags: list[str] | None,
    is_postgres: bool,
) -> list[ColumnElement[bool]]:
    """Build metadata predicates applied before list/search candidate selection.

    A keyword performs a case-insensitive partial match over document metadata.
    Every requested tag contributes one EXISTS predicate, giving the API's documented
    all-tags semantics without a PostgreSQL-only JSON operator.
    """
    conditions: list[ColumnElement[bool]] = []
    keyword_clean = keyword.strip() if keyword else ""
    if keyword_clean:
        keyword_pattern = f"%{keyword_clean}%"
        conditions.append(
            or_(
                Document.title.ilike(keyword_pattern),
                Document.code_number.ilike(keyword_pattern),
                Document.issuing_body.ilike(keyword_pattern),
                cast(Document.tags, String).ilike(keyword_pattern),
            )
        )

    for tag in normalize_tags(tags):
        conditions.append(_tag_exists_condition(tag, is_postgres))

    return conditions
