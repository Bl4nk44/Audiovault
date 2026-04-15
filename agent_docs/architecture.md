# Architecture — Audiovault

> Czytaj gdy dotykasz nowego modułu lub chcesz zrozumieć przepływ danych.

## System overview

Audiovault = self-hosted music library manager. Import playlist z URL → yt-dlp pobiera FLAC lokalnie → serwujesz przez własne API + kompatybilny Subsonic endpoint dla mobilnych klientów.

```
Frontend (React 19 :2137)
    ↕ REST /api/v1/*   ←→ Backend (FastAPI :8000)
    ↕ Socket.IO                ↕
                         PostgreSQL :5432
                         Redis :6379
                         /downloads/ (pliki FLAC/MP3)
```

## Backend — warstwy

```
api/
  v1/           ← REST endpoints (/api/v1/*)  — tylko orchestracja, ZERO logiki
  subsonic/     ← Subsonic API (/rest/*)       — osobny auth, XML lub JSON
services/       ← cała logika biznesowa
models/         ← SQLAlchemy ORM (async)
schemas/        ← Pydantic v2 (walidacja I/O)
providers/      ← zewnętrzne API (metadata + download)
core/           ← config, security, cache, exceptions
db/             ← engine, session, migrations base
```

## Przepływ: import playlisty

```
POST /api/v1/import/{platform}
  → route (api/v1/import_routes.py)       # tylko walidacja input
  → ImportService.import_playlist()        # orkiestracja
    → ProviderManager.get_provider(url)    # wybór providera
    → Provider.extract_playlist(url)       # Spotify/Deezer/etc API
    → TrackService.create_or_update()      # zapis do DB
    → DownloadManager.add_download()       # kolejka pobrań
      → yt-dlp (w ThreadPoolExecutor)      # pobieranie pliku
      → Socket.IO emit "download_progress" # live update do frontu
```

## Przepływ: stream pliku

```
GET /api/v1/stream/{track_id}
  → StreamService.get_stream_url()
  → zwraca URL do /stream/<filename>      # StaticFiles mount
  (plik FLAC serwowany bezpośrednio przez FastAPI StaticFiles)
```

## Subsonic API (/rest/*)

**Osobny system auth** — query params zamiast Bearer token:
- `u=username` + `p=password` (plaintext lub hex `enc:...`)  
- LUB `u=username` + `t=md5(password+salt)` + `s=salt`
- Zawsze: `v=1.16.1`, `c=client_name`, `f=json` (lub `f=xml`)

**Implementacja:**
```
app/api/subsonic/
  router.py         ← APIRouter, prefix="/rest", montuje wszystkie handlery
  auth.py           ← subsonic_auth() dependency — waliduje u/p/t/s
  utils.py          ← format_response(), error_response() → subsonic-response JSON
  handlers/
    system.py       ← ping, getLicense, getToken
    browse.py       ← getMusicFolders, getIndexes, getMusicDirectory, getArtist, getAlbum, getSong
    media.py        ← stream, download, getCoverArt, getLyrics
    search.py       ← search2, search3
    playlist.py     ← getPlaylists, getPlaylist, createPlaylist, deletePlaylist
    lists.py        ← getAlbumList, getAlbumList2, getStarred, getStarred2
    user.py         ← getUser
    info.py         ← getArtistInfo, getAlbumInfo
    lyrics.py       ← getLyrics
```

**Kompatybilni klienci:** Sonixd, Amperfy, DSub, Ultrasonic.

## Providers — pobieranie metadanych

```python
# base.py — ABC
class MusicProvider:
    name: str                                # 'spotify', 'tidal', etc.
    domains: list[str]                       # ['spotify.com', 'open.spotify.com']
    def can_handle(url: str) -> bool
    async def extract_playlist(url) -> PlaylistMetadata | None
    async def get_track(url) -> TrackMetadata | None

# manager.py — wybiera providera
ProviderManager.get_provider(url) → MusicProvider | None
```

**Dostępne providery:** Spotify, Tidal, Deezer, Apple Music, Amazon Music, YouTube, SoundCloud, MusicBrainz (metadata), Generic (yt-dlp fallback).

## Services — klucze

| Serwis | Plik | Odpowiedzialność |
|--------|------|-----------------|
| `DownloadManager` | `download_manager.py` | Kolejka + worker (yt-dlp w thread) |
| `SchedulerService` | `scheduler.py` | APScheduler — cron joby (sync, cleanup) |
| `SocketManager` | `socket_manager.py` | Socket.IO — live events do frontu |
| `CacheManager` | `core/cache.py` | Redis wrapper (get/set/delete) |
| `AuthManager` | `auth_manager.py` | JWT token + subsonic auth |
| `LibraryMaintenance` | `library_maintenance.py` | Rescan, integrity check |

## Frontend

```
src/
  api/        ← axios instances + request functions
  hooks/      ← TanStack Query hooks (useTrack, usePlaylists…)
  store/      ← Zustand slices (playback, ui, auth)
  components/ ← UI komponenty
  pages/      ← React Router pages
  types/      ← TypeScript interfaces
  i18n/       ← polskie stringi (PL locale)
```

**Socket.IO events z backendu:**
- `download_progress` → `{track_id, progress, status}`
- `download_complete` → `{track_id, file_path}`
- `download_error` → `{track_id, error}`

## Docker Compose — serwisy

| Serwis | Port | Wolumen |
|--------|------|---------|
| backend | 8000 | `./backend:/app`, `music_data:/downloads` |
| frontend | 2137 | `./frontend:/app` |
| db (postgres) | 5432 | `postgres_data:/var/lib/postgresql/data` |
| redis | 6379 | — |

## Kluczowe konwencje architektoniczne

- Routery **nie** zawierają logiki — tylko `service.method(params)` i zwracają response
- Serwisy **nie** importują routerów — jednokierunkowa zależność
- yt-dlp zawsze w `asyncio.get_event_loop().run_in_executor(None, ...)` — nigdy bezpośrednio w async
- DB queries z `selectinload()` dla relacji — nigdy lazy loading w async kontekście
- Nowe endpointy REST: `api/v1/` + plik serwisu + testy w `tests/api/` i `tests/services/`
- Nowy Subsonic endpoint: `api/subsonic/handlers/` + auth przez `subsonic_auth` dependency
