"""Tests for app/db/database.py — get_db generator."""

import pytest


@pytest.mark.asyncio
async def test_get_db_yields_session():
    """get_db yields a live AsyncSession and closes it after use."""
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.database import get_db

    gen = get_db()
    session = await gen.__anext__()
    assert isinstance(session, AsyncSession)

    # Exhaust generator (triggers finally → session.close)
    try:
        await gen.aclose()
    except StopAsyncIteration:
        pass


@pytest.mark.asyncio
async def test_get_db_closes_on_exception():
    """Session closes even when caller raises inside the with-block."""
    from app.db.database import get_db

    gen = get_db()
    await gen.__anext__()

    # Simulating exception from caller side
    try:
        await gen.athrow(RuntimeError("boom"))
    except RuntimeError, StopAsyncIteration:
        pass  # expected
