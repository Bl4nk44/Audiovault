"""Regression tests for fresh-install DB bootstrap.

The Alembic chain does not create the initial schema (base migration
fc0ebd8b67a8 ALTERs a pre-existing tracks table), so an empty database
must be bootstrapped with create_all + stamp head. Regression for the
fresh-install crash-loop introduced in 68b4f13.
"""

import sqlite3

import pytest
from alembic.script import ScriptDirectory

from app.db import bootstrap


def _tables_and_version(db_path):
    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    finally:
        conn.close()
    return tables, version


def test_empty_database_gets_full_schema_and_head_stamp(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    monkeypatch.setattr("app.core.config.settings.DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    bootstrap.main()

    tables, version = _tables_and_version(db_path)
    assert {"tracks", "users", "artists", "albums", "downloads", "playlists"} <= tables
    head = ScriptDirectory.from_config(bootstrap._alembic_config()).get_current_head()
    assert version == head


def test_second_run_takes_upgrade_path_and_is_noop(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    monkeypatch.setattr("app.core.config.settings.DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    bootstrap.main()
    _, version_first = _tables_and_version(db_path)

    # Second run simulates a container restart: DB is non-empty and stamped
    # at head, so the upgrade path must be a clean no-op.
    bootstrap.main()

    tables, version_second = _tables_and_version(db_path)
    assert "tracks" in tables
    assert version_second == version_first


def test_refuses_inconsistent_schema_with_alembic_version_but_no_tracks(tmp_path, monkeypatch):
    db_path = tmp_path / "weird.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
    conn.commit()
    conn.close()
    monkeypatch.setattr("app.core.config.settings.DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    with pytest.raises(RuntimeError, match="refusing to bootstrap"):
        bootstrap.main()
