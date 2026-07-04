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


async def _inspect_tables(url: str) -> set[str]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            return set(await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))
    finally:
        await engine.dispose()


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
    # Plain postgres:// URLs (documented in .env.example) need the async driver,
    # same normalization as app/db/database.py and migrations/env.py.
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    tables = asyncio.run(_inspect_tables(url))
    if _SENTINEL_TABLE in tables:
        logger.info("Existing database — running alembic upgrade head")
        command.upgrade(_alembic_config(), "head")
        return
    if "alembic_version" in tables:
        raise RuntimeError(
            "Database has an alembic_version table but no 'tracks' table — "
            "schema looks inconsistent; refusing to bootstrap. Inspect the database manually."
        )
    if tables:
        logger.warning("Database has tables but no '%s' — treating as fresh install", _SENTINEL_TABLE)
    logger.info("Empty database detected — creating schema and stamping Alembic head")
    asyncio.run(_create_schema(url))
    # Stamp immediately after create_all; if the process dies between the
    # two, the next boot would wrongly take the upgrade path.
    command.stamp(_alembic_config(), "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
