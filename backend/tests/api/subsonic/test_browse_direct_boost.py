"""
Direct handler calls to bypass FastAPI/AsyncClient coverage issues.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.api.subsonic.handlers.browse import (
    get_album,
    get_artist,
    get_artists,
    get_indexes,
    get_music_directory,
    get_song,
)
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from app.models.user import User


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def test_user():
    return User(id=1, username="test_user", is_active=True)


@pytest.mark.asyncio
async def test_get_indexes_direct(mock_db, test_user):
    # Mock artists result
    artist = Artist(id=uuid.uuid4(), name="Artist A")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [artist]
    mock_db.execute.side_effect = [
        mock_result,  # artists
        MagicMock(scalar=lambda: 1),  # album count
    ]

    resp = await get_indexes(f="json", current_user=test_user, db=mock_db)
    assert resp["subsonic-response"]["status"] == "ok"
    assert resp["subsonic-response"]["indexes"]["index"][0]["name"] == "A"


@pytest.mark.asyncio
async def test_get_artists_direct(mock_db, test_user):
    artist = Artist(id=uuid.uuid4(), name="Artist B")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [artist]
    mock_db.execute.side_effect = [
        mock_result,  # artists
        MagicMock(scalar=lambda: 2),  # album count
    ]

    resp = await get_artists(f="json", current_user=test_user, db=mock_db)
    assert resp["subsonic-response"]["artists"]["index"][0]["artist"][0]["name"] == "Artist B"


@pytest.mark.asyncio
async def test_get_artist_direct(mock_db, test_user):
    artist_id = uuid.uuid4()
    artist = Artist(id=artist_id, name="Artist C")
    album = Album(id=uuid.uuid4(), title="Album C", artist_id=artist_id, release_date="2020-01-01")

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: artist),  # artist
        MagicMock(scalars=lambda: MagicMock(all=lambda: [album])),  # albums
        MagicMock(scalar=lambda: 10),  # song count
        MagicMock(scalar=lambda: 300000),  # duration
    ]

    resp = await get_artist(id=str(artist_id), f="json", current_user=test_user, db=mock_db)
    assert resp["subsonic-response"]["artist"]["name"] == "Artist C"
    assert resp["subsonic-response"]["artist"]["album"][0]["name"] == "Album C"


@pytest.mark.asyncio
async def test_get_album_direct(mock_db, test_user):
    album_id = uuid.uuid4()
    artist_id = uuid.uuid4()
    album = Album(id=album_id, title="Album D", artist_id=artist_id, release_date="2021-01-01")
    artist = Artist(id=artist_id, name="Artist D")
    track = Track(id=uuid.uuid4(), title="Track D", album_id=album_id, duration_ms=200000)
    download = Download(id=1, status="completed")

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: album),  # album
        MagicMock(scalar_one_or_none=lambda: artist),  # artist
        MagicMock(all=lambda: [(track, download)]),  # tracks
    ]

    resp = await get_album(id=str(album_id), f="json", current_user=test_user, db=mock_db)
    assert resp["subsonic-response"]["album"]["name"] == "Album D"
    assert resp["subsonic-response"]["album"]["song"][0]["title"] == "Track D"


@pytest.mark.asyncio
async def test_get_song_direct(mock_db, test_user):
    track_id = uuid.uuid4()
    track = Track(id=track_id, title="Song E")
    download = Download(id=2, status="completed")

    mock_result = MagicMock()
    mock_result.first.return_value = (track, download)
    mock_db.execute.return_value = mock_result

    resp = await get_song(id=str(track_id), f="json", current_user=test_user, db=mock_db)
    assert resp["subsonic-response"]["song"]["title"] == "Song E"


@pytest.mark.asyncio
async def test_get_music_directory_artist_direct(mock_db, test_user):
    artist_id = uuid.uuid4()
    artist = Artist(id=artist_id, name="Artist F")
    album = Album(id=uuid.uuid4(), title="Album F", artist_id=artist_id, release_date="2022")

    # get_music_directory logic for artist ID
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: artist),  # check if artist
        MagicMock(scalars=lambda: MagicMock(all=lambda: [album])),  # list albums
        MagicMock(scalar=lambda: 5),  # song count
    ]

    resp = await get_music_directory(id=str(artist_id), f="json", current_user=test_user, db=mock_db)
    assert resp["subsonic-response"]["directory"]["name"] == "Artist F"
    assert resp["subsonic-response"]["directory"]["child"][0]["title"] == "Album F"


@pytest.mark.asyncio
async def test_get_music_directory_root_direct(mock_db, test_user):
    artist = Artist(id=uuid.uuid4(), name="Artist G", images={"profile": "url"})
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: [artist]))

    resp = await get_music_directory(id="1", f="json", current_user=test_user, db=mock_db)
    assert resp["subsonic-response"]["directory"]["id"] == "1"
    assert resp["subsonic-response"]["directory"]["child"][0]["title"] == "Artist G"


@pytest.mark.asyncio
async def test_get_music_directory_album_direct(mock_db, test_user):
    album_id = uuid.uuid4()
    album = Album(id=album_id, title="Album H", artist_id=uuid.uuid4())
    artist = Artist(id=album.artist_id, name="Artist H")
    track = Track(id=uuid.uuid4(), title="Track H")
    download = Download(id=3, status="completed")

    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: None),  # not an artist
        MagicMock(scalar_one_or_none=lambda: album),  # is an album
        MagicMock(scalar_one_or_none=lambda: artist),  # get artist
        MagicMock(all=lambda: [(track, download)]),  # list tracks
    ]

    resp = await get_music_directory(id=str(album_id), f="json", current_user=test_user, db=mock_db)
    assert resp["subsonic-response"]["directory"]["name"] == "Album H"
    assert resp["subsonic-response"]["directory"]["child"][0]["title"] == "Track H"
