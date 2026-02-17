# Common Issues & Solutions

## Download Issues

### Geo-Restricted Content
**Symptom:** "Video not available in your region" error

**Causes:**
- YouTube regional restrictions
- Platform licensing limitations

**Solutions:**
1. System automatically tries Invidious proxy
2. User can configure custom proxy in settings
3. Try alternative platform (e.g., SoundCloud)

**Prevention:**
- Keep yt-dlp updated
- Maintain list of working Invidious instances
- Implement proxy health checks

### yt-dlp Extractor Broken
**Symptom:** "Unable to extract" or "Unsupported URL" errors

**Causes:**
- Platform changed API/HTML structure
- yt-dlp version outdated

**Solutions:**
1. Update yt-dlp: `pip install --upgrade yt-dlp`
2. Check yt-dlp GitHub for known issues
3. Implement platform-specific fallback

**Code Location:** `app/services/download_service.py`

### Duplicate Downloads
**Symptom:** Same track downloaded multiple times

**Causes:**
- Different URLs for same track
- Metadata mismatch
- Cache not checked

**Solutions:**
- Check `DownloadHistory` table before download
- Normalize metadata (lowercase, remove special chars)
- Use audio fingerprinting (future enhancement)

**Code:**
```python
existing = await db.execute(
    select(DownloadHistory)
    .where(
        DownloadHistory.title == normalized_title,
        DownloadHistory.artist == normalized_artist
    )
)
if existing.scalar_one_or_none():
    return {"status": "already_exists"}
```

## Database Issues

### N+1 Query Problem
**Symptom:** Slow API responses, many database queries

**Solution:**
```python
# ❌ Bad
tracks = await db.execute(select(Track))
for track in tracks.scalars():
    playlist = await db.get(Playlist, track.playlist_id)

# ✅ Good
tracks = await db.execute(
    select(Track).options(selectinload(Track.playlist))
)
```

### Migration Conflicts
**Symptom:** Alembic revision conflicts

**Solutions:**
```bash
# Create merge revision
alembic merge heads

# Or downgrade and upgrade
alembic downgrade base
alembic upgrade head
```

### Database Locked (SQLite)
**Symptom:** "Database is locked" errors

**Causes:**
- Concurrent write operations
- Long-running transaction

**Solutions:**
1. Use PostgreSQL for production
2. Implement retry logic
3. Reduce transaction duration

## Authentication Issues

### JWT Token Expired
**Symptom:** 401 Unauthorized after period of inactivity

**Solution:**
- Implement refresh token mechanism
- Frontend auto-refreshes before expiry
- Redirect to login on 401

**Code Location:** `app/core/security.py`, `frontend/src/api/client.ts`

### CORS Errors
**Symptom:** Browser blocks API requests

**Solution:**
```python
# backend/.env
BACKEND_CORS_ORIGINS=http://localhost:2137,https://yourdomain.com
```

## Frontend Issues

### WebSocket Disconnects
**Symptom:** Real-time updates stop working

**Causes:**
- Network issues
- Server restart
- Reverse proxy timeout

**Solutions:**
```typescript
// Implement auto-reconnect
const ws = new WebSocket(url);

ws.onclose = () => {
  setTimeout(() => {
    connectWebSocket();
  }, 5000);
};
```

### State Not Updating
**Symptom:** UI doesn't reflect changes after action

**Solution:**
```typescript
// Invalidate React Query cache
const mutation = useMutation({
  mutationFn: downloadTrack,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['tracks'] });
  },
});
```

## Deployment Issues

### Docker Network Issues
**Symptom:** Frontend can't reach backend

**Solution:**
```yaml
# docker-compose.yml
services:
  frontend:
    environment:
      - BACKEND_URL=http://backend:8000  # Use service name
```

### Reverse Proxy 502 Bad Gateway
**Symptom:** Nginx/Traefik shows 502 error

**Solutions:**
1. Check backend is running: `docker compose logs backend`
2. Verify network: `docker compose exec frontend curl backend:8000/health`
3. Check proxy config:
```nginx
location /api {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### File Permissions
**Symptom:** Can't write to `/app/downloads` or `/app/data`

**Solution:**
```yaml
# docker-compose.yml
volumes:
  - ./downloads:/app/downloads:rw  # Add :rw
user: "1000:1000"  # Match host user
```

## Performance Issues

### Slow Download Speed
**Causes:**
- Network bandwidth limitation
- yt-dlp downloading video instead of audio
- No parallel downloads

**Solutions:**
1. Configure format selection:
```python
ytdl_opts = {
    'format': 'bestaudio/best',  # Audio only
    'concurrent_fragment_downloads': 5
}
```

2. Enable parallel downloads in settings

### High Memory Usage
**Causes:**
- Large files loaded into memory
- Memory leaks
- Too many concurrent operations

**Solutions:**
- Stream files instead of loading fully
- Limit concurrent downloads
- Monitor with `docker stats`

## API Issues

### Rate Limiting
**Symptom:** 429 Too Many Requests

**Solution:**
- Implement exponential backoff
- Use caching for frequent queries
- Batch operations when possible

### Subsonic Compatibility
**Symptom:** Mobile app can't connect

**Solutions:**
1. Enable legacy auth in app settings
2. Use plaintext password (not token)
3. Verify endpoint: `/rest/ping.view`
4. Check HTTPS/SSL certificate

**Tested Apps:**
- ✅ Sonixd (desktop)
- ✅ Symfonium (Android)
- ⚠️ Amperfy (iOS) - requires legacy auth
- ✅ DSub (Android)

## Troubleshooting Workflow

1. **Check Logs:**
```bash
docker compose logs backend --tail=100
docker compose logs frontend --tail=100
```

2. **Verify Database:**
```bash
docker compose exec backend python -c "from app.db.session import engine; print('DB OK')"
```

3. **Test API:**
```bash
curl http://localhost:8000/health
```

4. **Check Browser Console:**
- Open DevTools
- Check Console for errors
- Check Network tab for failed requests

5. **Restart Services:**
```bash
docker compose restart backend
```
