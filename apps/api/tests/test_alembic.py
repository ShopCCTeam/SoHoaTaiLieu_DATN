"""Unit tests cho Alembic migration revision chain.

Apply/rollback tests cần Postgres trong CI (integration).
Unit: chỉ verify revision chain tồn tại.

Local: pytest SKIP các test cần Postgres.
CI: chạy với postgres service — pytest.fail nếu không có.
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
    return ScriptDirectory(alembic_path)


def test_alembic_has_0001_revision(script_dir: ScriptDirectory) -> None:
    """Verify revision 0001 tồn tại."""
    revisions = {r.revision for r in script_dir.walk_revisions()}
    assert "0001" in revisions


def test_alembic_has_0002_revision(script_dir: ScriptDirectory) -> None:
    """Verify revision 0002 tồn tại."""
    revisions = {r.revision for r in script_dir.walk_revisions()}
    assert "0002" in revisions


def test_alembic_has_0003_revision(script_dir: ScriptDirectory) -> None:
    """Verify revision 0003 tồn tại."""
    revisions = {r.revision for r in script_dir.walk_revisions()}
    assert "0003" in revisions


def test_alembic_has_0004_revision(script_dir: ScriptDirectory) -> None:
    """Verify revision 0004 tồn tại."""
    revisions = {r.revision for r in script_dir.walk_revisions()}
    assert "0004" in revisions


def test_alembic_0002_downrevs_to_0001(script_dir: ScriptDirectory) -> None:
    """0002 phải có down_revision = 0001."""
    revisions = {r.revision: r for r in script_dir.walk_revisions()}
    assert revisions["0002"].down_revision == "0001"


def test_alembic_0003_downrevs_to_0002(script_dir: ScriptDirectory) -> None:
    """0003 phải có down_revision = 0002."""
    revisions = {r.revision: r for r in script_dir.walk_revisions()}
    assert revisions["0003"].down_revision == "0002"


def test_alembic_0004_downrevs_to_0003(script_dir: ScriptDirectory) -> None:
    """0004 phải có down_revision = 0003."""
    revisions = {r.revision: r for r in script_dir.walk_revisions()}
    assert revisions["0004"].down_revision == "0003"


def test_alembic_has_0005_revision(script_dir: ScriptDirectory) -> None:
    """Verify revision 0005 tồn tại."""
    revisions = {r.revision for r in script_dir.walk_revisions()}
    assert "0005" in revisions


def test_alembic_0005_downrevs_to_0004(script_dir: ScriptDirectory) -> None:
    """0005 phải có down_revision = 0004."""
    revisions = {r.revision: r for r in script_dir.walk_revisions()}
    assert revisions["0005"].down_revision == "0004"


def test_alembic_has_0006_revision(script_dir: ScriptDirectory) -> None:
    """Verify revision 0006 tồn tại."""
    revisions = {r.revision for r in script_dir.walk_revisions()}
    assert "0006" in revisions


def test_alembic_0006_downrevs_to_0005(script_dir: ScriptDirectory) -> None:
    """0006 phải có down_revision = 0005."""
    revisions = {r.revision: r for r in script_dir.walk_revisions()}
    assert revisions["0006"].down_revision == "0005"


def test_alembic_head_is_0006(script_dir: ScriptDirectory) -> None:
    """Head revision phải là 0006."""
    assert script_dir.get_current_head() == "0006"


def test_alembic_base_is_none(script_dir: ScriptDirectory) -> None:
    """Base (không có down_revision) phải là 0001."""
    bases = {r.revision for r in script_dir.walk_revisions() if r.down_revision is None}
    assert "0001" in bases


@pytest.mark.integration
def test_alembic_upgrade_downgrade_on_postgres() -> None:
    """Apply + rollback trên Postgres thật. Cần postgres service trong CI.

    Trong CI: probe fail → pytest.fail (Postgres phải chạy).
    Ngoài CI: skip (expected).

    URL là `postgresql+asyncpg://` — alembic/env.py dùng create_async_engine
    bắt buộc driver async. `postgresql://` (psycopg2) sẽ raise
    InvalidRequestError ở CI khi có PG thật.
    """
    import socket

    from alembic import command
    from alembic.config import Config

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_TEST_DB", os.environ.get("POSTGRES_DB", "ctsv_test"))
    user = os.environ.get("POSTGRES_USER", "ctsv_test")
    password = os.environ.get("POSTGRES_PASSWORD", "ctsv_test")
    url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

    _IN_CI = os.environ.get("CI", "").lower() in {"1", "true", "yes"}

    def _skip_or_fail(msg: str) -> None:
        if _IN_CI:
            pytest.fail(f"CI phải có Postgres: {msg}")
        pytest.skip(msg)

    # Probe TCP trước — skip/fail nhanh nếu Postgres không có.
    try:
        with socket.create_connection((host, int(port)), timeout=1):
            pass
    except OSError as exc:
        # OSError cover ConnectionRefusedError + socket.gaierror + TimeoutError
        # trên mọi platform. Tuple explicit là dư — simplify.
        _skip_or_fail(f"Postgres không khả dụng tại {host}:{port}: {exc!r}")

    # Alembic folder ở `apps/api/alembic/` (không phải `tests/alembic/`).
    here = Path(__file__).parent
    cfg = Config()
    cfg.set_main_option("script_location", str(here.parent / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)

    # Upgrade → downgrade → upgrade round-trip
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "-1")
    command.upgrade(cfg, "head")
