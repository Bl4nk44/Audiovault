from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.models.album import Album
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_subsonic_media_ssrf_prevention(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
):
    """
    Test that /getCoverArt.view refuses to fetch images from untrusted domains.
    """
    evil_album_id = uuid4()

    # Poison DB
    evil_album = Album(
        id=evil_album_id,
        title="Evil Album",
        images={
            "300": "http://internal-host.local:8080/admin",
            "url": "http://internal-host.local:8080/admin",
        },
    )
    db_session.add(evil_album)
    await db_session.commit()

    from app.api.subsonic.handlers.media import get_cover_art

    with patch("app.api.subsonic.handlers.media._get_remote_image", new_callable=AsyncMock) as mock_remote:
        try:
            await get_cover_art(
                id=f"al-{evil_album_id}",
                db=db_session,
                current_user=admin_user,
            )
        except Exception:
            pass

        # The request shouldn't trigger an external fetch to internal-host.local
        mock_remote.assert_not_called()


@pytest.mark.asyncio
async def test_settings_youtube_verify_ssrf_prevention(
    client: AsyncClient,
    admin_token_headers: dict,
):
    """
    Test that the /verify/youtube endpoint safely encodes the API key
    to prevent URL parameter injection / SSRF.
    """

    evil_key = "fake_key&other=val"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.status_code = 400

        await client.post(
            "/api/v1/settings/verify/youtube",
            json={"apiKey": evil_key},
            headers=admin_token_headers,
        )

        # Check what URL was actually requested
        # We expect httpx.get to be called with params dictionary, NOT an f-string
        assert mock_get.called

        # httpx.get allows passing url and params.
        # If the key was injected in the raw string, it would have 'fake_key&other=val' literal
        call_args = mock_get.call_args.args

        url_called = call_args[0] if call_args else ""

        assert "fake_key&other=val" not in str(url_called)
