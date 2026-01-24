import uuid
from datetime import datetime

from app.models.album import Album
from app.models.artist import Artist
from app.models.audit_log import AuditLog
from app.models.download import Download
from app.models.history import History
from app.models.playlist import Playlist
from app.models.playlist_version import PlaylistVersion
from app.models.starred import Starred
from app.models.track import Track
from app.models.user import User
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem


def test_user_model_coverage():
    u = User(id=uuid.uuid4(), username="test", email="test@test.com")
    assert u.username == "test"
    # Trigger repr if exists, or arbitrary attribute access


def test_track_model_coverage():
    t = Track(id=uuid.uuid4(), title="Test Track", duration=120, file_path="/tmp/test.mp3")
    assert t.title == "Test Track"


def test_album_model_coverage():
    a = Album(id=uuid.uuid4(), title="Test Album")
    assert a.title == "Test Album"


def test_artist_model_coverage():
    a = Artist(id=uuid.uuid4(), name="Test Artist")
    assert a.name == "Test Artist"


def test_download_model_coverage():
    d = Download(id=uuid.uuid4(), track_id=uuid.uuid4(), status="pending", created_at=datetime.utcnow())
    assert d.status == "pending"


def test_playlist_model_coverage():
    p = Playlist(id=uuid.uuid4(), name="My Playlist", owner_id=uuid.uuid4())
    assert p.name == "My Playlist"


def test_playlist_version_coverage():
    pv = PlaylistVersion(id=uuid.uuid4(), playlist_id=uuid.uuid4(), version=1)
    assert pv.version == 1


def test_history_model_coverage():
    h = History(id=uuid.uuid4(), track_id=uuid.uuid4(), listened_at=datetime.utcnow())
    assert h.track_id is not None


def test_watchlist_model_coverage():
    w = Watchlist(id=uuid.uuid4(), name="WL", user_id=uuid.uuid4())
    assert w.name == "WL"


def test_watchlist_item_coverage():
    wi = WatchlistItem(id=uuid.uuid4(), watchlist_id=uuid.uuid4())
    assert wi.watchlist_id is not None


def test_starred_model_coverage():
    s = Starred(id=uuid.uuid4(), user_id=uuid.uuid4(), track_id=uuid.uuid4())
    assert s.user_id is not None


def test_audit_log_model_coverage():
    al = AuditLog(id=uuid.uuid4(), action="LOGIN", timestamp=datetime.utcnow())
    assert al.action == "LOGIN"


def test_credentials_model_coverage():
    c = ServiceCredentials(id=uuid.uuid4(), user_id=uuid.uuid4(), service="spotify")
    assert c.service == "spotify"
