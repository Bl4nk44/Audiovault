# Common Issues & Solutions

## Download Issues

### Geo-Restricted Content
**Symptom:** "Video not available in your region" error

**Solutions:**
1. System automatycznie próbuje Invidious proxy
2. User może skonfigurować własny proxy w ustawieniach
3. Spróbuj alternatywnej platformy (np. SoundCloud)

**Prevention:** Aktualizuj yt-dlp, utrzymuj listę działających instancji Invidious

**Code Location:** `app/services/download_service.py`

### yt-dlp Extractor Broken
**Symptom:** "Unable to extract" lub "Unsupported URL"

**Solutions:**
1. `pip install --upgrade yt-dlp`
2. Sprawdź GitHub yt-dlp w poszukiwaniu znanych problemów
3. Zaimplementuj platform-specific fallback

### Duplicate Downloads
**Symptom:** Ten sam utwór pobrany wielokrotnie

**Solution:** Sprawdź tabelę `DownloadHistory` przed pobraniem, normalizuj metadata

```python
existing = await db.execute(
    select(DownloadHistory).where(
        DownloadHistory.title == normalized_title,
        DownloadHistory.artist == normalized_artist
    )
)
if existing.scalar_one_or_none():
    return {"status": "already_exists"}
```

## Database Issues

### N+1 Query Problem
```python
# ❌ Bad
for track in tracks.scalars():
    playlist = await db.get(Playlist, track.playlist_id)

# ✅ Good
tracks = await db.execute(select(Track).options(selectinload(Track.playlist)))
```

### Migration Conflicts
```bash
alembic merge heads       # Stwórz merge revision
alembic downgrade base && alembic upgrade head  # lub pełny reset
```

### Database Locked (SQLite)
**Causes:** Concurrent writes, długa transakcja
**Solutions:** Użyj PostgreSQL w produkcji, dodaj retry logic, skróć transakcje

## Authentication Issues

### JWT Token Expired
**Solution:** Refresh token mechanism, frontend auto-refresh przed wygaśnięciem, redirect na login przy 401
**Code:** `app/core/security.py`, `frontend/src/api/client.ts`

### CORS Errors
```bash
# backend/.env
BACKEND_CORS_ORIGINS=http://localhost:2137,https://yourdomain.com
```

## Frontend Issues

### WebSocket Disconnects
```typescript
ws.onclose = () => setTimeout(() => connectWebSocket(), 5000); // auto-reconnect
```

### State Not Updating
```typescript
onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tracks'] })
```

## Deployment Issues

### Docker Network Issues
```yaml
environment:
  - BACKEND_URL=http://backend:8000  # Use service name, not localhost
```

### File Permissions
```yaml
volumes:
  - ./downloads:/app/downloads:rw
user: "1000:1000"  # Match host user
```

### Reverse Proxy 502
1. `docker compose logs backend` — sprawdź czy backend działa
2. `docker compose exec frontend curl backend:8000/health`
3. Sprawdź konfigurację proxy_pass

## Performance Issues

### Slow Downloads
```python
ytdl_opts = { 'format': 'bestaudio/best', 'concurrent_fragment_downloads': 5 }
```

### Subsonic Compatibility
1. Włącz legacy auth w ustawieniach apki
2. Użyj plaintext password (nie token)
3. Zweryfikuj endpoint: `/rest/ping.view`

## Troubleshooting Workflow
```bash
docker compose logs backend --tail=100
docker compose logs frontend --tail=100
curl http://localhost:8000/health
docker compose restart backend
```
