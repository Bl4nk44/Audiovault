import xml.etree.ElementTree as ET
from uuid import uuid4

from app.api.subsonic.utils import build_song_response
from app.schemas.subsonic.base import dict_to_xml


def test_song_attributes_mandatory_fields():
    """Verify built song response has mandatory parent and other fields."""

    class MockTrack:
        id = uuid4()
        title = "Test Song"
        artist = "Test Artist"
        album = "Test Album"
        album_id = uuid4()
        artist_id = uuid4()
        duration_ms = 180000
        created_at = None
        isrc = None
        metadata_content = {"year": "2023", "track": "5"}

    class MockDownload:
        file_path = "/music/song.mp3"
        file_size = 5000000

    track = MockTrack()
    download = MockDownload()

    song_dict = build_song_response(track, download)

    # Check parent
    assert "parent" in song_dict
    assert song_dict["parent"] == str(track.album_id)

    # Check track number
    assert "track" in song_dict
    assert song_dict["track"] == 5

    # Check year
    assert song_dict["year"] == 2023

    # Check XML generation
    xml_output = dict_to_xml("song", song_dict)
    root = ET.fromstring(xml_output)

    assert root.get("parent") == str(track.album_id)
    assert root.get("track") == "5"


def test_song_attributes_fallback_parent():
    """Verify parent fallback triggers if no album."""

    class MockTrackNoAlbum:
        id = uuid4()
        title = "Single"
        artist = None
        album = None
        album_id = None
        artist_id = None
        duration_ms = 0
        created_at = None
        isrc = None
        metadata_content = {}

    track = MockTrackNoAlbum()
    song_dict = build_song_response(track)

    assert song_dict["parent"] == "root"
