import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.album import Album
from app.models.artist import Artist
from app.models.download import Download
from app.models.track import Track
from app.models.user import User


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
async def sample_tracks(db_session: AsyncSession, test_user: User):
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    await db_session.flush()

    album = Album(title="Test Album", artist_id=artist.id)
    db_session.add(album)
    await db_session.flush()

    tracks = []
    for i in range(5):
        track = Track(
            title=f"Song {i}",
            artist_id=artist.id,
            album_id=album.id,
            metadata_content={"genre": "Rock" if i % 2 == 0 else "Jazz"},
        )
        tracks.append(track)
        db_session.add(track)
        await db_session.flush()  # Flush to get track.id

        # Add Download
        download = Download(
            track_id=track.id, user_id=test_user.id, status="completed", file_path=f"/test_audio/test_song_{i}.mp3"
        )
        db_session.add(download)

    await db_session.commit()
    return tracks


@pytest.mark.asyncio
async def test_get_genres(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get("/rest/getGenres.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    genres = data["subsonic-response"]["genres"]["genre"]
    assert len(genres) == 2
    genre_names = [g["value"] for g in genres]
    assert "Rock" in genre_names
    assert "Jazz" in genre_names


@pytest.mark.asyncio
async def test_get_album_list_2(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get("/rest/getAlbumList2.view?type=newest&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "albumList2" in data["subsonic-response"]
    assert len(data["subsonic-response"]["albumList2"]["album"]) > 0


@pytest.mark.asyncio
async def test_get_random_songs(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get("/rest/getRandomSongs.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "randomSongs" in data["subsonic-response"]
    assert len(data["subsonic-response"]["randomSongs"]["song"]) > 0


@pytest.mark.asyncio
async def test_get_random_songs_admin(client: AsyncClient, admin_user):
    """Use admin_user fixture (same pattern as other subsonic tests) to ensure coverage."""
    params = {"u": admin_user.username, "p": "admin", "c": "pytest", "v": "1.16.1", "f": "json"}
    response = await client.get("/rest/getRandomSongs.view", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "randomSongs" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_top_songs(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get("/rest/getTopSongs.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "topSongs" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_top_songs_by_artist(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get(
        "/rest/getTopSongs.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json&artist=Test+Artist"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "topSongs" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_similar_songs_valid(client: AsyncClient, test_user: User, sample_tracks):
    track_id = str(sample_tracks[0].id)
    response = await client.get(
        f"/rest/getSimilarSongs.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json&id={track_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
    assert "similarSongs" in data["subsonic-response"]


@pytest.mark.asyncio
async def test_get_similar_songs_invalid_id(client: AsyncClient, test_user: User):
    response = await client.get("/rest/getSimilarSongs.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json&id=not-a-uuid")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
    assert data["subsonic-response"]["error"]["code"] == 10


@pytest.mark.asyncio
async def test_get_similar_songs_not_found(client: AsyncClient, test_user: User):
    import uuid

    unknown_id = str(uuid.uuid4())
    response = await client.get(
        f"/rest/getSimilarSongs.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json&id={unknown_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "failed"
    assert data["subsonic-response"]["error"]["code"] == 70


@pytest.mark.asyncio
async def test_get_album_list_random_type(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get("/rest/getAlbumList.view?type=random&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_get_album_list_alphabetical_type(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get(
        "/rest/getAlbumList.view?type=alphabetical&u=testuser&p=testpass&c=test&v=1.16.1&f=json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_get_album_list_by_name_type(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get("/rest/getAlbumList.view?type=byName&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


@pytest.mark.asyncio
async def test_get_album_list_default_type(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get("/rest/getAlbumList.view?type=starred&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"


# --- getAlbumList (folder) vs getAlbumList2 (ID3): correct wrapper + keys ---
# getAlbumList is the v1/folder-style endpoint and must return the "albumList"
# wrapper with directory-style entries (title/isDir). getAlbumList2 is the ID3
# endpoint and must return "albumList2" with ID3 entries (name/artistId).
# The old code returned "albumList2" for both, so folder-mode clients (DSub,
# play:Sub) saw an empty list.


@pytest.mark.asyncio
async def test_get_album_list_returns_album_list_wrapper(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get(
        "/rest/getAlbumList.view?type=alphabeticalByName&u=testuser&p=testpass&c=DSub&v=1.13.0&f=json"
    )
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "ok"
    assert "albumList" in body
    albums = body["albumList"]["album"]
    assert any(a["title"] == "Test Album" for a in albums)
    assert all(a.get("isDir") is True for a in albums)


@pytest.mark.asyncio
async def test_get_album_list2_uses_id3_keys(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get(
        "/rest/getAlbumList2.view?type=alphabeticalByName&u=testuser&p=testpass&c=test&v=1.16.1&f=json"
    )
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    albums = body["albumList2"]["album"]
    assert any(a.get("name") == "Test Album" for a in albums)
    assert all("artistId" in a for a in albums)


@pytest.mark.asyncio
async def test_get_album_list_by_genre(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get(
        "/rest/getAlbumList2.view?type=byGenre&genre=Rock&u=testuser&p=testpass&c=test&v=1.16.1&f=json"
    )
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "ok"
    assert "albumList2" in body


@pytest.mark.asyncio
async def test_get_album_list_by_year(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get(
        "/rest/getAlbumList.view?type=byYear&fromYear=1900&toYear=2100&u=testuser&p=testpass&c=test&v=1.16.1&f=json"
    )
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "ok"
    assert "albumList" in body


# --- Unknown endpoint must degrade softly: HTTP 200 + Subsonic error, not 404 ---
# Subsonic clients expect HTTP 200 with an error envelope for every request.
# A raw HTTP 404 makes some clients abort the whole sync.


@pytest.mark.asyncio
async def test_unknown_endpoint_returns_200_error_envelope(client: AsyncClient, test_user: User):
    response = await client.get("/rest/getThisDoesNotExist.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "failed"
    assert body["error"]["code"] == 70


# --- Endpoints clients browse for data through (must return data, not soft-fail) ---


@pytest.mark.asyncio
async def test_get_songs_by_genre(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get("/rest/getSongsByGenre.view?genre=Rock&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "ok"
    songs = body["songsByGenre"]["song"]
    # sample_tracks: genre "Rock" on even indices (0,2,4) => 3 songs
    assert len(songs) == 3
    assert all(s["title"].startswith("Song") for s in songs)


@pytest.mark.asyncio
async def test_get_songs_by_genre_empty(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get(
        "/rest/getSongsByGenre.view?genre=Nonexistent&u=testuser&p=testpass&c=test&v=1.16.1&f=json"
    )
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "ok"
    assert body["songsByGenre"]["song"] == []


@pytest.mark.asyncio
async def test_start_scan(client: AsyncClient, test_user: User):
    response = await client.get("/rest/startScan.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "ok"
    assert body["scanStatus"]["scanning"] is False


@pytest.mark.asyncio
async def test_get_videos_empty(client: AsyncClient, test_user: User):
    response = await client.get("/rest/getVideos.view?u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "ok"
    assert body["videos"]["video"] == []


@pytest.mark.asyncio
async def test_get_album_info2(client: AsyncClient, test_user: User, sample_tracks):
    album_id = str(sample_tracks[0].album_id)
    response = await client.get(f"/rest/getAlbumInfo2.view?id={album_id}&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "ok"
    assert "albumInfo" in body


@pytest.mark.asyncio
async def test_get_album_info_folder(client: AsyncClient, test_user: User, sample_tracks):
    album_id = str(sample_tracks[0].album_id)
    response = await client.get(f"/rest/getAlbumInfo.view?id={album_id}&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "ok"
    assert "largeImageUrl" in body["albumInfo"]


@pytest.mark.asyncio
async def test_get_album_info_invalid_id(client: AsyncClient, test_user: User):
    response = await client.get("/rest/getAlbumInfo.view?id=not-a-uuid&u=testuser&p=testpass&c=test&v=1.16.1&f=json")
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "failed"
    assert body["error"]["code"] == 10


@pytest.mark.asyncio
async def test_get_album_info_not_found(client: AsyncClient, test_user: User):
    import uuid

    response = await client.get(
        f"/rest/getAlbumInfo.view?id={uuid.uuid4()}&u=testuser&p=testpass&c=test&v=1.16.1&f=json"
    )
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "failed"
    assert body["error"]["code"] == 70


@pytest.mark.asyncio
async def test_get_album_list_alphabetical_by_artist(client: AsyncClient, test_user: User, sample_tracks):
    response = await client.get(
        "/rest/getAlbumList2.view?type=alphabeticalByArtist&u=testuser&p=testpass&c=test&v=1.16.1&f=json"
    )
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "ok"
    assert "albumList2" in body


@pytest.mark.asyncio
async def test_get_album_list_unknown_type_falls_back(client: AsyncClient, test_user: User, sample_tracks):
    # Unknown sort type must hit the default ordering branch, not error.
    response = await client.get(
        "/rest/getAlbumList2.view?type=somethingWeird&u=testuser&p=testpass&c=test&v=1.16.1&f=json"
    )
    assert response.status_code == 200
    body = response.json()["subsonic-response"]
    assert body["status"] == "ok"
    assert "albumList2" in body


def test_genre_expr_postgres_branch():
    # _genre_expr picks a dialect-specific extraction; the Postgres branch is not
    # exercised by the SQLite test DB, so cover it directly with a fake dialect.
    from types import SimpleNamespace

    from app.api.subsonic.handlers.lists import _genre_expr

    fake_db = SimpleNamespace(bind=SimpleNamespace(dialect=SimpleNamespace(name="postgresql")))
    expr = _genre_expr(fake_db)  # type: ignore[arg-type]
    assert "json_extract_path_text" in str(expr).lower()
