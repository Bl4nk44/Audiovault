from unittest.mock import AsyncMock, Mock

import pytest

from app.services.listenbrainz_service import ListenBrainzError, ListenBrainzService


@pytest.fixture
def service():
    svc = ListenBrainzService()
    svc.client = AsyncMock()
    return svc


def _resp(status: int = 200, body: dict | None = None):
    r = Mock()
    r.status_code = status
    r.json.return_value = body or {}
    r.content = b"x" if body is not None else b""
    r.raise_for_status = Mock()
    return r


# --- validate_token ---


@pytest.mark.asyncio
async def test_validate_token_returns_username(service):
    service.client.get.return_value = _resp(200, {"valid": True, "user_name": "alice"})
    assert await service.validate_token("tok") == "alice"
    headers = service.client.get.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Token tok"


@pytest.mark.asyncio
async def test_validate_token_invalid_raises(service):
    service.client.get.return_value = _resp(200, {"valid": False})
    with pytest.raises(ListenBrainzError):
        await service.validate_token("bad")


# --- submitting ---


@pytest.mark.asyncio
async def test_submit_now_playing_shape(service):
    service.client.post.return_value = _resp(200, {"status": "ok"})
    await service.submit_now_playing("tok", "Track", "Artist", album="Album")

    path, kwargs = service.client.post.call_args[0][0], service.client.post.call_args.kwargs
    assert path == "/1/submit-listens"
    body = kwargs["json"]
    assert body["listen_type"] == "playing_now"
    md = body["payload"][0]["track_metadata"]
    assert md == {
        "artist_name": "Artist",
        "track_name": "Track",
        "release_name": "Album",
        "additional_info": {"submission_client": "Audiovault"},
    }
    assert "listened_at" not in body["payload"][0]


@pytest.mark.asyncio
async def test_submit_listen_includes_timestamp(service):
    service.client.post.return_value = _resp(200, {"status": "ok"})
    await service.submit_listen("tok", "T", "A", listened_at=1712345678)
    body = service.client.post.call_args.kwargs["json"]
    assert body["listen_type"] == "single"
    assert body["payload"][0]["listened_at"] == 1712345678


@pytest.mark.asyncio
async def test_rate_limit_429_raises(service):
    service.client.post.return_value = _resp(429)
    with pytest.raises(ListenBrainzError):
        await service.submit_listen("tok", "T", "A", listened_at=1)


# --- stats / history ---


@pytest.mark.asyncio
async def test_get_top_artists_maps_and_ranges(service):
    service.client.get.return_value = _resp(
        200,
        {"payload": {"artists": [{"artist_name": "Nirvana", "artist_mbid": "m1", "listen_count": 42}, {"foo": 1}]}},
    )
    out = await service.get_top_artists("alice", period="7day", limit=10)
    assert out == [{"name": "Nirvana", "mbid": "m1", "playcount": 42}]
    assert service.client.get.call_args.kwargs["params"] == {"range": "week", "count": 10}


@pytest.mark.asyncio
async def test_get_top_tracks_maps(service):
    service.client.get.return_value = _resp(
        200,
        {
            "payload": {
                "recordings": [
                    {"track_name": "Come As You Are", "artist_name": "Nirvana", "recording_mbid": "r1"},
                    {"track_name": "no artist"},
                ]
            }
        },
    )
    out = await service.get_top_tracks("alice")
    assert len(out) == 1
    assert out[0]["name"] == "Come As You Are"
    assert out[0]["mbid"] == "r1"


@pytest.mark.asyncio
async def test_get_recent_tracks_maps(service):
    service.client.get.return_value = _resp(
        200,
        {"payload": {"listens": [{"listened_at": 5, "track_metadata": {"track_name": "T", "artist_name": "A"}}]}},
    )
    out = await service.get_recent_tracks("alice")
    assert out == [{"name": "T", "artist": "A", "album": None, "listened_at": 5}]


@pytest.mark.asyncio
async def test_no_content_204_returns_empty(service):
    service.client.get.return_value = _resp(204, None)
    assert await service.get_top_artists("alice") == []
    assert await service.get_recommended_recording_mbids("alice") == []


@pytest.mark.asyncio
async def test_recommended_recording_mbids(service):
    service.client.get.return_value = _resp(
        200, {"payload": {"mbids": [{"recording_mbid": "a", "score": 9}, {"score": 1}]}}
    )
    assert await service.get_recommended_recording_mbids("alice") == ["a"]


@pytest.mark.asyncio
async def test_get_profile_combines_count_and_similar(service):
    async def fake_get(path, token=None, params=None):
        if path.endswith("/listen-count"):
            return {"payload": {"count": 999}}
        if path.endswith("/similar-users"):
            return {"payload": [{"user_name": "bob", "similarity": 0.8}]}
        return None

    service._get = fake_get  # type: ignore[method-assign]
    profile = await service.get_profile("alice")
    assert profile["user"]["playcount"] == 999
    assert profile["user"]["url"] == "https://listenbrainz.org/user/alice/"
    assert profile["similar_users"] == [{"name": "bob", "similarity": 0.8}]


@pytest.mark.asyncio
async def test_get_recent_tracks_empty_payload(service):
    service.client.get.return_value = _resp(200, {"payload": {"listens": []}})
    assert await service.get_recent_tracks("alice") == []


@pytest.mark.asyncio
async def test_get_recent_tracks_no_data(service):
    service.client.get.return_value = _resp(204, None)
    assert await service.get_recent_tracks("alice") == []


@pytest.mark.asyncio
async def test_get_recommended_mbids_no_data(service):
    service.client.get.return_value = _resp(204, None)
    assert await service.get_recommended_recording_mbids("alice") == []


@pytest.mark.asyncio
async def test_get_listen_count(service):
    service.client.get.return_value = _resp(200, {"payload": {"count": 4321}})
    assert await service.get_listen_count("alice") == 4321
    service.client.get.return_value = _resp(204, None)
    assert await service.get_listen_count("alice") == 0


@pytest.mark.asyncio
async def test_get_similar_users_variants(service):
    service.client.get.return_value = _resp(200, {"payload": [{"user_name": "bob", "similarity": 0.9}, {"x": 1}]})
    assert await service.get_similar_users("alice") == [{"name": "bob", "similarity": 0.9}]

    service.client.get.return_value = _resp(200, {"payload": "not-a-list"})
    assert await service.get_similar_users("alice") == []

    service.client.get.return_value = _resp(204, None)
    assert await service.get_similar_users("alice") == []


@pytest.mark.asyncio
async def test_get_profile_survives_source_errors(service):
    async def boom(*_a, **_kw):
        raise ListenBrainzError("down")

    service._get = boom  # type: ignore[method-assign]
    profile = await service.get_profile("alice")
    assert profile["user"]["playcount"] == 0
    assert profile["similar_users"] == []


@pytest.mark.asyncio
async def test_get_post_http_error_wrapped(service):
    import httpx

    service.client.post.side_effect = httpx.ConnectError("boom")
    with pytest.raises(ListenBrainzError):
        await service.submit_now_playing("tok", "T", "A")

    service.client.get.side_effect = httpx.ConnectError("boom")
    with pytest.raises(ListenBrainzError):
        await service.validate_token("tok")
