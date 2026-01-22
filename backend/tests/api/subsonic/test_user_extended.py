"""Extended tests for Subsonic user handlers - star, unstar, rating, scrobble."""
import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.fixture
def subsonic_auth_params(admin_user):
    return {
        "u": admin_user.username,
        "p": "admin",
        "c": "pytest",
        "v": "1.16.1",
        "f": "json"
    }


class TestStarUnstar:
    @pytest.mark.asyncio
    async def test_star_track(self, client: AsyncClient, subsonic_auth_params, sample_track):
        """Test starring a track."""
        params = {**subsonic_auth_params, "id": str(sample_track.id)}
        response = await client.get("/rest/star.view", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["subsonic-response"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_star_invalid_id(self, client: AsyncClient, subsonic_auth_params):
        """Test starring with invalid UUID."""
        params = {**subsonic_auth_params, "id": "invalid-uuid"}
        response = await client.get("/rest/star.view", params=params)
        # Should succeed silently (skips invalid IDs)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_star_multiple_tracks(self, client: AsyncClient, subsonic_auth_params, sample_track):
        """Test starring multiple items."""
        params = {
            **subsonic_auth_params,
            "id": [str(sample_track.id), str(uuid4())]  # One valid, one non-existent
        }
        response = await client.get("/rest/star.view", params=params)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unstar_track(self, client: AsyncClient, subsonic_auth_params, sample_track):
        """Test unstarring a track."""
        # First star it
        star_params = {**subsonic_auth_params, "id": str(sample_track.id)}
        await client.get("/rest/star.view", params=star_params)

        # Then unstar
        response = await client.get("/rest/unstar.view", params=star_params)
        assert response.status_code == 200
        data = response.json()
        assert data["subsonic-response"]["status"] == "ok"


class TestGetStarred:
    @pytest.mark.asyncio
    async def test_get_starred_empty(self, client: AsyncClient, subsonic_auth_params):
        """Test getting starred items when empty."""
        response = await client.get("/rest/getStarred.view", params=subsonic_auth_params)
        assert response.status_code == 200
        data = response.json()
        assert data["subsonic-response"]["status"] == "ok"
        assert "starred" in data["subsonic-response"]

    @pytest.mark.asyncio
    async def test_get_starred2(self, client: AsyncClient, subsonic_auth_params):
        """Test getStarred2 endpoint (ID3 format)."""
        response = await client.get("/rest/getStarred2.view", params=subsonic_auth_params)
        assert response.status_code == 200
        data = response.json()
        assert data["subsonic-response"]["status"] == "ok"
        assert "starred2" in data["subsonic-response"]


class TestSetRating:
    @pytest.mark.asyncio
    async def test_set_rating_valid(self, client: AsyncClient, subsonic_auth_params, sample_track):
        """Test setting a valid rating."""
        params = {**subsonic_auth_params, "id": str(sample_track.id), "rating": 5}
        response = await client.get("/rest/setRating.view", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["subsonic-response"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_set_rating_zero_removes(self, client: AsyncClient, subsonic_auth_params, sample_track):
        """Test that rating 0 removes the rating."""
        # First set a rating
        params = {**subsonic_auth_params, "id": str(sample_track.id), "rating": 3}
        await client.get("/rest/setRating.view", params=params)

        # Then remove it with 0
        params["rating"] = 0
        response = await client.get("/rest/setRating.view", params=params)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_set_rating_invalid_value(self, client: AsyncClient, subsonic_auth_params, sample_track):
        """Test rating with invalid value."""
        params = {**subsonic_auth_params, "id": str(sample_track.id), "rating": 10}
        response = await client.get("/rest/setRating.view", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["subsonic-response"]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_set_rating_invalid_id(self, client: AsyncClient, subsonic_auth_params):
        """Test rating with invalid track ID."""
        params = {**subsonic_auth_params, "id": "bad-id", "rating": 3}
        response = await client.get("/rest/setRating.view", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["subsonic-response"]["status"] == "failed"


class TestScrobble:
    @pytest.mark.asyncio
    async def test_scrobble_submission(self, client: AsyncClient, subsonic_auth_params, sample_track):
        """Test full scrobble submission."""
        params = {
            **subsonic_auth_params,
            "id": str(sample_track.id),
            "submission": True
        }
        response = await client.get("/rest/scrobble.view", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["subsonic-response"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_scrobble_now_playing(self, client: AsyncClient, subsonic_auth_params, sample_track):
        """Test now playing update (no submission)."""
        params = {
            **subsonic_auth_params,
            "id": str(sample_track.id),
            "submission": False
        }
        response = await client.get("/rest/scrobble.view", params=params)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_scrobble_with_timestamp(self, client: AsyncClient, subsonic_auth_params, sample_track):
        """Test scrobble with custom timestamp."""
        import time
        params = {
            **subsonic_auth_params,
            "id": str(sample_track.id),
            "time": int(time.time() * 1000) - 60000  # 1 minute ago
        }
        response = await client.get("/rest/scrobble.view", params=params)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_scrobble_invalid_id(self, client: AsyncClient, subsonic_auth_params):
        """Test scrobble with invalid track ID."""
        params = {**subsonic_auth_params, "id": "invalid"}
        response = await client.get("/rest/scrobble.view", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["subsonic-response"]["status"] == "failed"


class TestGetNowPlaying:
    @pytest.mark.asyncio
    async def test_get_now_playing(self, client: AsyncClient, subsonic_auth_params):
        """Test getting now playing list."""
        response = await client.get("/rest/getNowPlaying.view", params=subsonic_auth_params)
        assert response.status_code == 200
        data = response.json()
        assert data["subsonic-response"]["status"] == "ok"
        assert "nowPlaying" in data["subsonic-response"]


class TestGetRandomSongs:
    @pytest.mark.asyncio
    async def test_get_random_songs_default(self, client: AsyncClient, subsonic_auth_params):
        """Test getting random songs with defaults."""
        response = await client.get("/rest/getRandomSongs.view", params=subsonic_auth_params)
        assert response.status_code == 200
        data = response.json()
        assert data["subsonic-response"]["status"] == "ok"
        assert "randomSongs" in data["subsonic-response"]

    @pytest.mark.asyncio
    async def test_get_random_songs_with_size(self, client: AsyncClient, subsonic_auth_params):
        """Test getting specific number of random songs."""
        params = {**subsonic_auth_params, "size": 5}
        response = await client.get("/rest/getRandomSongs.view", params=params)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_random_songs_max_size(self, client: AsyncClient, subsonic_auth_params):
        """Test that size is capped at 500."""
        params = {**subsonic_auth_params, "size": 1000}
        response = await client.get("/rest/getRandomSongs.view", params=params)
        assert response.status_code == 200
