# Technical Context: Audiovault

## Stack

| Warstwa | Technologia |
|---------|------------|
| Backend | FastAPI (Python 3.11+), SQLAlchemy 2.0 async, Alembic, APScheduler |
| Download | yt-dlp, Mutagen (ID3 tags) |
| Database | SQLite (default) / PostgreSQL (production), Redis (cache) |
| Frontend | React 18, TypeScript, TailwindCSS v4, Framer Motion, Vite |
| State | React Query (server) + Context API (theme/auth) |
| Deploy | Docker Compose, Nginx/Traefik compatible |
| Auth | JWT tokens (HS256, 7d expiry), Subsonic token-based |

## Critical Code Paths

### Download Pipeline
1. `app/api/endpoints/downloads.py` — request validation
2. `app/services/extractors/*` — URL extraction per platform
3. `app/services/download_service.py` — duplicate check + fallback logic
4. yt-dlp execution (format: `bestaudio/best`)
5. `app/services/metadata_service.py` — ID3 tagging
6. DB record → WebSocket progress notification

### Fallback Chain
1. Original URL + yt-dlp
2. Alternative queries ("Official Audio", "Lyrics")
3. Cross-platform (SoundCloud if YouTube fails)
4. Invidious proxy (geo-restricted content)

### Subsonic API
- `app/api/endpoints/subsonic.py`, wersja v1.16.1
- Range request streaming support
- Przetestowano z: Sonixd ✅, Symfonium ✅, Amperfy ⚠️ (legacy auth), DSub ✅

## Dependencies to Watch
- **yt-dlp**: breaking changes w extractors — aktualizuj regularnie
- **FastAPI/Pydantic v2**: migracja zakończona
- **SQLAlchemy 2.0**: async patterns w użyciu
- **TailwindCSS v4**: bleeding edge alpha

## Testing
- Backend: pytest + pytest-asyncio, cel 80%+ coverage
- Frontend: Vitest + React Testing Library
- E2E: planowany Playwright
- Security: Semgrep, Trivy, Snyk, GitGuardian

## Deployment
- Volumes: `/app/data` (DB), `/app/downloads` (muzyka)
- Env vars: 20+ opcji konfiguracyjnych
- HTTPS wymagane w produkcji, CORS skonfigurowany
- `user: "1000:1000"` w compose dla uprawnień do plików
