# Fresh-Install DB Bootstrap Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fresh installs (empty database, Postgres or SQLite) boot successfully instead of crash-looping on `relation "tracks" does not exist`.

**Architecture:** The Alembic chain never creates the initial schema — the base migration `fc0ebd8b67a8` ALTERs pre-existing tables. Historically a startup fallback (`create_all` + `alembic stamp head`) bootstrapped fresh databases; commit `68b4f13` removed it as a "duplicate", breaking every fresh install since. Fix: a dedicated `app/db/bootstrap.py` module that detects an empty database and does `Base.metadata.create_all()` + `alembic stamp head`, otherwise runs `alembic upgrade head`. `entrypoint.sh` calls it instead of raw `alembic upgrade head`. A pytest regression test runs the bootstrap against an empty SQLite DB — this is the CI guard (backend pytest already runs in `ci.yml`).

**Tech Stack:** Python 3.14, SQLAlchemy async, Alembic (async env.py), pytest.

**Key facts for the implementer (zero-context primer):**

- Alembic layout: ini at `backend/alembic.ini`, `script_location = app/db/migrations`, env at `backend/app/db/migrations/env.py`. `env.py` **always** takes the DB URL from `app.core.config.settings.DATABASE_URL` (ignores the ini URL) and runs migrations via `asyncio.run(...)` — so Alembic commands must be invoked from **sync** code, never inside a running event loop.
- All models register on `Base` from `app/db/base.py`; importing `app.models` populates `Base.metadata` (side-effect imports in `backend/app/models/__init__.py`).
- Container: Dockerfile `ENTRYPOINT ["/app/entrypoint.sh"]`, WORKDIR is `/app` (= repo `backend/`). `entrypoint.sh` currently runs `alembic upgrade head` then `exec "$@"`.
- `backend/app/main.py:211` has a comment claiming migrations run in entrypoint.sh — update it in Task 3.
- Existing installs have `alembic_version` at head → must keep taking the `upgrade` path untouched.
- Running tests (per project workflow — running stack is a stale prod image, use an ephemeral dev container):
  `docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --build --entrypoint pytest backend tests/test_db_bootstrap.py -v`

---

### Task 1: Failing regression tests for the bootstrap

**Files:**
- Test (create): `backend/tests/test_db_bootstrap.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Regression tests for fresh-install DB bootstrap.

The Alembic chain does not create the initial schema (base migration
fc0ebd8b67a8 ALTERs a pre-existing tracks table), so an empty database
must be bootstrapped with create_all + stamp head. Regression for the
fresh-install crash-loop introduced in 68b4f13.
"""

import sqlite3

from alembic.script import ScriptDirectory

from app.db import bootstrap


def _tables_and_version(db_path):
    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    finally:
        conn.close()
    return tables, version


def test_empty_database_gets_full_schema_and_head_stamp(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    monkeypatch.setattr(
        "app.core.config.settings.DATABASE_URL", f"sqlite+aiosqlite:///{db_path}"
    )

    bootstrap.main()

    tables, version = _tables_and_version(db_path)
    assert {"tracks", "users", "artists", "albums", "downloads", "playlists"} <= tables
    head = ScriptDirectory.from_config(bootstrap._alembic_config()).get_current_head()
    assert version == head


def test_second_run_takes_upgrade_path_and_is_noop(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    monkeypatch.setattr(
        "app.core.config.settings.DATABASE_URL", f"sqlite+aiosqlite:///{db_path}"
    )

    bootstrap.main()
    _, version_first = _tables_and_version(db_path)

    # Second run simulates a container restart: DB is non-empty and stamped
    # at head, so the upgrade path must be a clean no-op.
    bootstrap.main()

    tables, version_second = _tables_and_version(db_path)
    assert "tracks" in tables
    assert version_second == version_first
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --build --entrypoint pytest backend tests/test_db_bootstrap.py -v
```
Expected: FAIL/ERROR at collection with `ImportError`/`ModuleNotFoundError: app.db.bootstrap` (module does not exist yet).

- [ ] **Step 3: Commit the failing tests**

```bash
git add backend/tests/test_db_bootstrap.py
git commit -m "test(db): add failing regression tests for fresh-install bootstrap"
```

---

### Task 2: Implement `app/db/bootstrap.py`

**Files:**
- Create: `backend/app/db/bootstrap.py`
- Test: `backend/tests/test_db_bootstrap.py` (from Task 1)

- [ ] **Step 1: Write the module**

```python
"""Database bootstrap for container startup.

The Alembic chain does not create the initial schema — the base migration
(fc0ebd8b67a8) ALTERs tables assumed to already exist. An empty database
must therefore be initialized with Base.metadata.create_all() and stamped
at head; a non-empty database just runs `alembic upgrade head`.

Must run before the app boots (called from entrypoint.sh). Alembic's
env.py calls asyncio.run(), so main() is sync and must never be invoked
from inside a running event loop.
"""

import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  — registers all models on Base.metadata
from app.db.base import Base

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Core table from the very first migration's assumptions; if it is missing,
# the database has never held an Audiovault schema.
_SENTINEL_TABLE = "tracks"


def _alembic_config() -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    # Absolute path so the command works regardless of CWD (tests run
    # outside /app; the ini's script_location is relative).
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "app" / "db" / "migrations"))
    return cfg


async def _is_empty_database(url: str) -> bool:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    finally:
        await engine.dispose()
    return _SENTINEL_TABLE not in tables


async def _create_schema(url: str) -> None:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


def main() -> None:
    from app.core.config import settings

    url = settings.DATABASE_URL
    if asyncio.run(_is_empty_database(url)):
        logger.info("Empty database detected — creating schema and stamping Alembic head")
        asyncio.run(_create_schema(url))
        command.stamp(_alembic_config(), "head")
    else:
        logger.info("Existing database — running alembic upgrade head")
        command.upgrade(_alembic_config(), "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
```

Notes for the implementer:
- `env.py` reads the URL from `settings.DATABASE_URL` itself, which is why `main()` doesn't pass a URL to Alembic — the monkeypatch in tests covers both the inspection and the Alembic subprocess-free command calls.
- `command.stamp`/`command.upgrade` are sync entry points; env.py internally does `asyncio.run()`. Calling them from async code would raise `RuntimeError: asyncio.run() cannot be called from a running event loop` — keep `main()` sync.

- [ ] **Step 2: Run the tests, verify they pass**

Run:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --build --entrypoint pytest backend tests/test_db_bootstrap.py -v
```
Expected: 2 passed.

- [ ] **Step 3: Run the full backend suite (no regressions)**

Run:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --entrypoint pytest backend --cov=app -q
```
Expected: all tests pass, coverage of `app/db/bootstrap.py` ≥ 80%.

- [ ] **Step 4: Lint**

Run: `ruff check backend/app/db/bootstrap.py backend/tests/test_db_bootstrap.py && ruff format --check backend/app/db/bootstrap.py backend/tests/test_db_bootstrap.py`
Expected: no findings.

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/bootstrap.py
git commit -m "fix(db): bootstrap schema on empty database before alembic

Fresh installs crash-looped since 68b4f13 removed the create_all
fallback: the alembic chain never creates the initial schema, so
'alembic upgrade head' fails on an empty DB with
'relation \"tracks\" does not exist' (Postgres) or an ALTER TABLE
syntax error (SQLite). Detect an empty database, create_all + stamp
head; existing databases keep the plain upgrade path."
```

---

### Task 3: Wire bootstrap into container startup

**Files:**
- Modify: `backend/entrypoint.sh`
- Modify: `backend/app/main.py:211` (stale comment)

- [ ] **Step 1: Replace the raw alembic call in `backend/entrypoint.sh`**

New full content:

```sh
#!/bin/sh
set -e

echo "Bootstrapping database (initial schema / migrations)..."
python -m app.db.bootstrap

echo "Starting application..."
exec "$@"
```

- [ ] **Step 2: Update the stale comment in `backend/app/main.py`**

Replace:
```python
    # Migrations run in entrypoint.sh (alembic upgrade head) before the app boots.
```
with:
```python
    # DB schema is bootstrapped in entrypoint.sh (app.db.bootstrap) before the app boots.
```

- [ ] **Step 3: End-to-end verify — fresh Postgres install boots**

This reproduces the user's exact scenario (empty volume, first boot). The volume is dedicated to Audiovault, created fresh here.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
sleep 15
docker compose logs backend | grep -E "Empty database|Bootstrapping|error|Error" | head
curl -sf http://localhost:8000/health && echo OK
```
Expected: log shows `Empty database detected — creating schema and stamping Alembic head`, no crash-loop, health check prints `OK`.

- [ ] **Step 4: Verify restart takes the upgrade path (existing-DB case)**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
sleep 10
docker compose logs --since 1m backend | grep -E "Existing database|error" | head
curl -sf http://localhost:8000/health && echo OK
```
Expected: log shows `Existing database — running alembic upgrade head`, health `OK`.

- [ ] **Step 5: Commit**

```bash
git add backend/entrypoint.sh backend/app/main.py
git commit -m "fix(startup): run db bootstrap in entrypoint instead of raw alembic upgrade"
```

---

## Out of scope (deliberate)

- **SQLite as supported prod backend / dialect-aware rewrite of `fc0ebd8b67a8`** — separate decision, parked earlier. This fix makes fresh SQLite boots work too (empty DB → create_all path never touches the broken migration), but non-empty SQLite DBs upgrading through the chain remain unsupported.
- **`DATABASE_URL` fail-fast / removal of the `sqlite+aiosqlite:///dummy` fallback** — parked, separate small change.
- **Squashing the migration chain into a real initial-schema migration** — cleaner long-term, but risky to hand-write (must reproduce the exact pre-`fc0ebd8b67a8` schema) and unnecessary once bootstrap owns the empty-DB case.

## Self-review

- Spec coverage: empty-DB Postgres fix (Tasks 1–3), empty-DB SQLite fixed by same path (Task 1 tests run on SQLite), CI guard = pytest test in existing `ci.yml` pytest run, existing installs untouched (Task 1 test 2 + Task 3 step 4). ✓
- No placeholders; all code complete. ✓
- Names consistent: `bootstrap.main()`, `_alembic_config()`, `_is_empty_database()` used identically across tasks. ✓
