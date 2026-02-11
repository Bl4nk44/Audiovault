from datetime import datetime
from uuid import uuid4

import pytest
from app.api.subsonic.utils import (
    build_album_response,
    build_song_response,
    format_duration,
    format_subsonic_date,
    get_content_type,
    get_cover_art_id,
    parse_cover_art_id,
    parse_subsonic_id,
)


def test_format_subsonic_date():
    assert format_subsonic_date(None) is None
    dt = datetime(2024, 1, 15, 10, 30)
    assert format_subsonic_date(dt) == "2024-01-15T10:30:00.000Z"


def test_format_duration():
    assert format_duration(None) == 0
    assert format_duration(60000) == 60


def test_parse_subsonic_id():
    uid = uuid4()
    assert parse_subsonic_id(str(uid)) == uid
    with pytest.raises(ValueError):
        parse_subsonic_id("invalid-uuid")


def test_get_cover_art_id():
    uid = uuid4()
    assert get_cover_art_id(album_id=uid) == f"al-{uid}"
    assert get_cover_art_id(track_id=uid) == f"tr-{uid}"
    assert get_cover_art_id(artist_id=uid) == f"ar-{uid}"
    assert get_cover_art_id() is None


def test_parse_cover_art_id():
    uid = uuid4()
    assert parse_cover_art_id(f"al-{uid}") == ("al", uid)
    assert parse_cover_art_id(str(uid)) == ("unknown", uid)


def test_get_content_type():
    assert get_content_type("test.mp3") == "audio/mpeg"
    assert get_content_type("test.FLAC") == "audio/flac"
    assert get_content_type("no_ext") == "application/octet-stream"


def test_build_song_response_minimal():
    class MockTrack:
        id = uuid4()
        title = "Title"
        artist = "Artist"
        album = "Album"
        duration_ms = 180000
        created_at = datetime.now()
        artist_id = None
        album_id = None
        metadata_content = {}
        isrc = None

    track = MockTrack()
    response = build_song_response(track)
    assert response["id"] == str(track.id)
    assert response["parent"] == "root"


def test_build_song_response_full():
    class MockTrack:
        def __init__(self):
            self.id = uuid4()
            self.title = "Title"
            self.artist = "Artist"
            self.album = "Album"
            self.duration_ms = 180000
            self.created_at = datetime.now()
            self.artist_id = uuid4()
            self.album_id = uuid4()
            self.metadata_content = {"genre": "Rock", "year": "2024", "track": "1"}
            self.isrc = "ISRC123"

    track = MockTrack()
    response = build_song_response(track)
    assert response["albumId"] == str(track.album_id)
    assert response["artistId"] == str(track.artist_id)
    assert response["genre"] == "Rock"
    assert response["year"] == 2024
    assert response["track"] == 1


def test_build_album_response_minimal():
    class MockAlbum:
        id = uuid4()
        title = "Album"
        artist = None
        artist_id = None
        created_at = datetime.now()
        release_date = "2024-01-01"

    album = MockAlbum()
    response = build_album_response(album, 10)
    assert response["id"] == str(album.id)
    assert response["songCount"] == 10
    assert response["year"] == 2024
