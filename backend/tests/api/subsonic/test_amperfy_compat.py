"""
Test Amperfy compatibility for Subsonic API.

These tests specifically check endpoints that Amperfy uses
that were causing issues (404s and compatibility problems).
"""

import pytest
from app.core.security import get_password_hash
from app.models.artist import Artist
from app.models.user import User
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def test_user(db_session: AsyncSession):
    user = User(
        username="testuser", email="test@example.com", hashed_password=get_password_hash("testpass"), is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_artist(db_session: AsyncSession):
    artist = Artist(name="Test Artist", bio="Test bio")
    db_session.add(artist)
    await db_session.commit()
    await db_session.refresh(artist)
    return artist


@pytest.mark.asyncio
async def test_get_artist_info2(client: AsyncClient, test_user: User, sample_artist: Artist):
    """Test getArtistInfo2.view returns valid response (not 404)."""
    response = await client.get(
        f"/rest/getArtistInfo2.view?id={sample_artist.id}&u=testuser&p=testpass&c=test&v=1.16.1&f=json"
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Body: {response.text}"
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "artistInfo2" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_podcasts(client: AsyncClient, test_user: User):
    """Test getPodcasts.view returns empty list (not 404)."""
    response = await client.get(
        "/rest/getPodcasts.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json"
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Body: {response.text}"
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "podcasts" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_genres(client: AsyncClient, test_user: User):
    """Test getGenres.view returns valid response (not 404)."""
    response = await client.get(
        "/rest/getGenres.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json"
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Body: {response.text}"
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "genres" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_artist_info2_xml_format(client: AsyncClient, test_user: User, sample_artist: Artist):
    """Test getArtistInfo2.view returns valid XML (Amperfy uses XML by default)."""
    # Amperfy doesn't send f= parameter, so default XML should be returned
    response = await client.get(
        f"/rest/getArtistInfo2.view?id={sample_artist.id}&u=testuser&p=testpass&c=Amperfy&v=1.11.0"
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Body: {response.text}"
    # Should be XML
    assert response.headers.get("content-type", "").startswith("application/xml") or \
           response.headers.get("content-type", "").startswith("text/xml"), \
           f"Expected XML content-type, got: {response.headers.get('content-type')}"
    # Basic XML structure check
    assert '<?xml version="1.0"' in response.text or 'subsonic-response' in response.text


@pytest.mark.asyncio
async def test_get_podcasts_xml_format(client: AsyncClient, test_user: User):
    """Test getPodcasts.view returns valid XML for Amperfy."""
    response = await client.get(
        "/rest/getPodcasts.view?u=testuser&p=testpass&c=Amperfy&v=1.11.0&includeEpisodes=false"
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Body: {response.text}"
