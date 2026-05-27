from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.album import Album
from app.models.track import Track
from app.models.user import User


@pytest.mark.asyncio
async def test_stream_album_cover_open_redirect_prevention(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_token_headers: dict,
):
    """
    Test that even if an Album record has a poisoned image URL in the DB,
    the /album/{id}/cover endpoint refuses to redirect to untrusted domains.
    """
    evil_album_id = uuid4()

    # Poison DB
    evil_album = Album(
        id=evil_album_id,
        title="Evil Album",
        images={
            "300": "http://evil.com/phishing",
            "640": "http://evil.com/phishing",
        },
    )
    db_session.add(evil_album)
    await db_session.commit()

    # Attempt to get album cover redirect
    response = await client.get(
        f"/api/v1/stream/album/{evil_album_id}/cover",
        headers=admin_token_headers,
        follow_redirects=False,
    )

    # We expect this to fail (400 or 404) and NOT be a redirect (302/307)
    assert response.status_code != 302
    assert response.status_code != 307
    assert response.status_code == 400 or response.status_code == 404


@pytest.mark.asyncio
async def test_stream_track_cover_open_redirect_prevention(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_token_headers: dict,
):
    """
    Test that even if a Track's Album record has a poisoned image URL in the DB,
    the /{id}/cover endpoint refuses to redirect to untrusted domains.
    """
    evil_album_id = uuid4()
    evil_track_id = uuid4()

    # Poison DB
    evil_album = Album(
        id=evil_album_id,
        title="Evil Album",
        images={
            "300": "https://phishing.site/login",
            "640": "https://phishing.site/login",
        },
    )

    evil_track = Track(
        id=evil_track_id,
        title="Evil Track",
        album_id=evil_album_id,
    )

    db_session.add(evil_album)
    db_session.add(evil_track)
    await db_session.commit()

    # Attempt to get track cover redirect
    response = await client.get(
        f"/api/v1/stream/{evil_track_id}/cover",
        headers=admin_token_headers,
        follow_redirects=False,
    )

    # We expect this to fail (400 or 404) and NOT be a redirect (302/307)
    assert response.status_code != 302
    assert response.status_code != 307
    assert response.status_code == 400 or response.status_code == 404
