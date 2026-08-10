"""Unit tests cho Alembic migration revision chain.

Apply/rollback tests cần Postgres trong CI (integration).
Unit: chỉ verify revision chain tồn tại.

Local: pytest SKIP các test cần Postgres.
CI: chạy với postgres service.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from alembic.script import ScriptDirectory


@pytest.fixture
def script_dir() -> ScriptDirectory:
    """Alembic script directory — đọc trực tiếp từ filesystem."""
    here = Path(__file__).parent
    alembic_path = here.parent / "alembic"
    # ScriptDirectory nhận path trực tiếp
    return ScriptDirectory(alembic_path)


def test_alembic_has_0001_revision(script_dir: ScriptDirectory) -> None:
    """Verify revision 0001 tồn tại."""
    revisions = {r.revision for r in script_dir.walk_revisions()}
    assert "0001" in revisions


def test_alembic_has_0002_revision(script_dir: ScriptDirectory) -> None:
    """Verify revision 0002 tồn tại."""
    revisions = {r.revision for r in script_dir.walk_revisions()}
    assert "0002" in revisions


def test_alembic_0002_downrevs_to_0001(script_dir: ScriptDirectory) -> None:
    """0002 phải có down_revision = 0001."""
    revisions = {r.revision: r for r in script_dir.walk_revisions()}
    assert revisions["0002"].down_revision == "0001"


def test_alembic_head_is_0002(script_dir: ScriptDirectory) -> None:
    """Head revision phải là 0002."""
    assert script_dir.get_current_head() == "0002"


def test_alembic_base_is_none(script_dir: ScriptDirectory) -> None:
    """Base (không có down_revision) phải là 0001."""
    bases = {r.revision for r in script_dir.walk_revisions() if r.down_revision is None}
    assert "0001" in bases


@pytest.mark.integration
def test_alembic_upgrade_downgrade_on_postgres() -> None:
    """Apply + rollback trên Postgres thật. Cần postgres service trong CI."""
    from alembic import command
    from alembic.config import Config

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "ctsv_test")
    user = os.environ.get("POSTGRES_USER", "ctsv_test")
    password = os.environ.get("POSTGRES_PASSWORD", "ctsv_test")
    url = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    here = Path(__file__).parent
    cfg = Config()
    cfg.set_main_option("script_location", str(here / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)

    # Upgrade → downgrade → upgrade round-trip
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "-1")
    command.upgrade(cfg, "head")
