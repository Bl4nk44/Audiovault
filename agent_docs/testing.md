# Testing Guide — Audiovault

> Czytaj ten plik gdy piszesz lub debugujesz testy.

## Uruchamianie testów

```bash
# Wszystkie testy (przez Docker)
docker compose exec backend pytest --cov=app --cov-report=term-missing

# Szybko (SQLite in-memory, bez Dockera) — do lokalnego TDD
cd backend
PYTHONPATH=. DATABASE_URL="sqlite+aiosqlite:///./test.db" \
  REDIS_URL="redis://localhost:6379/0" \
  JWT_SECRET_KEY="test_secret_key_for_ci_tests_only" \
  pytest tests/ -v --tb=short

# Jeden plik
pytest tests/api/test_auth.py -v

# Jedna funkcja
pytest tests/api/test_auth.py::test_login_success -v

# Z coverage dla konkretnego modułu
pytest tests/services/ --cov=app/services --cov-report=term-missing
```

## Fixtures (conftest.py)

Wszystkie fixtures są w `backend/tests/conftest.py`. Scope: `function` (izolacja per test).

| Fixture | Co daje | Kiedy używać |
|---------|---------|--------------|
| `db_session` | AsyncSession → SQLite in-memory, fresh per test | Testy serwisów z DB |
| `client` | AsyncClient (httpx) + DB override + wszystkie mocki | Testy API endpoints |
| `admin_user` | User z `is_active=True`, username="admin" | Potrzebujesz usera w DB |
| `admin_token_headers` | `{"Authorization": "Bearer <token>"}` | Chronione endpointy |
| `normal_user` / `normal_user_token_headers` | Jak wyżej, bez uprawnień admina | Testy autoryzacji |
| `sample_track` | Track z `spotify_id="test_spotify_id"` | Testy library/stream |
| `mock_cache_manager` | Redis patchowany, `get` → None | Automatycznie w `client` |
| `mock_scheduler` | APScheduler nie startuje | Automatycznie w `client` |
| `mock_download_manager` | DownloadManager mockowany | Automatycznie w `client` |
| `mock_library_maintenance` | LibraryMaintenance mockowana | Automatycznie w `client` |

**`client` fixture automatycznie składa wszystkie mocki** — używaj go dla endpoint testów, nie łącz ręcznie.

## Wzorce testów

### Test endpointu (użyj `client`)

```python
@pytest.mark.asyncio
async def test_get_tracks(client: AsyncClient, admin_token_headers: dict):
    response = await client.get("/api/v1/browse/tracks", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
```

### Test serwisu (użyj `db_session`)

```python
@pytest.mark.asyncio
async def test_create_playlist(db_session: AsyncSession):
    from app.services.playlist_service import PlaylistService
    svc = PlaylistService(db_session)
    playlist = await svc.create(name="Test", user_id=uuid.uuid4())
    assert playlist.name == "Test"
```

### Test z mockiem zewnętrznego providera

```python
@pytest.mark.asyncio
async def test_spotify_import(client: AsyncClient, admin_token_headers: dict):
    with patch("app.services.spotify_service.SpotifyService.get_playlist") as mock_get:
        mock_get.return_value = {"tracks": [...], "name": "My Playlist"}
        response = await client.post(
            "/api/v1/import/spotify",
            json={"playlist_url": "https://open.spotify.com/playlist/123"},
            headers=admin_token_headers,
        )
    assert response.status_code == 201
```

### Test Subsonic API

Subsonic używa query params, nie Bearer token. Auth: `u=`, `p=`, `t=` + `s=`, `v=`, `c=`.

```python
@pytest.mark.asyncio
async def test_subsonic_ping(client: AsyncClient):
    response = await client.get("/rest/ping.view", params={
        "u": "admin", "p": "admin",   # lub t= + s= dla token auth
        "v": "1.16.1", "c": "test", "f": "json"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["subsonic-response"]["status"] == "ok"
```

## Konfiguracja pytest

`backend/pyproject.toml` lub `pytest.ini`:
- `asyncio_mode = "auto"` — wszystkie `async def test_*` działają bez dekoratora `@pytest.mark.asyncio`
- Ale dla pewności zawsze dodawaj dekorator (ruff to wymusza)

## Typowe błędy

| Błąd | Przyczyna | Fix |
|------|-----------|-----|
| `RuntimeError: no running event loop` | Fixture bez `async def` wywołuje async code | Zmień na `async def fixture` |
| `MissingGreenlet` (SQLAlchemy) | `await` brakuje przy operacji DB | Dodaj `await` |
| `429 Too Many Requests` w testach | Rate limiter nie jest mockowany | Użyj `client` fixture (już mockuje) |
| `ConnectionRefusedError` (Redis) | `cache_manager` nie jest mockowany | Dodaj `mock_cache_manager` do fixture |
| Test minie lokalnie, pada w Docker | Różnica SQLite vs PostgreSQL dialekt | Sprawdź `ARRAY`, `JSON`, `UUID` kolumny |

## Struktura katalogów testów

```
tests/
  conftest.py          ← wszystkie fixtures
  api/                 ← testy przez HTTP client
  services/            ← testy serwisów z db_session
  providers/           ← testy providerów (mock HTTP)
  core/                ← testy utils, security, config
  utils/               ← helpery testowe
```
