import os

from app.config.lastfm_config import LastfmConfig


def test_lastfm_config_loads_from_env():
    """Sprawdź czy config ładuje zmienne z .env (mockowane environment vars)"""
    os.environ["LASTFM_API_KEY"] = "test_key"
    os.environ["LASTFM_API_SECRET"] = "test_secret"
    os.environ["LASTFM_CALLBACK_URL"] = "http://localhost/callback"

    config = LastfmConfig()

    assert config.API_KEY == "test_key"
    assert config.API_SECRET == "test_secret"
    assert config.BASE_URL == "http://ws.audioscrobbler.com/2.0/"
    assert config.CALLBACK_URL == "http://localhost/callback"

    # Cleanup to not affect other tests if run in same process
    del os.environ["LASTFM_API_KEY"]
    del os.environ["LASTFM_API_SECRET"]
    del os.environ["LASTFM_CALLBACK_URL"]


def test_lastfm_config_defaults():
    """Sprawdź domyślne wartości"""
    config = LastfmConfig(API_KEY="test", API_SECRET="test", CALLBACK_URL="http://test")
    assert config.CACHE_TTL == 86400
    assert config.SCROBBLE_THRESHOLD == 50
    assert config.SCROBBLE_ENABLED is True
