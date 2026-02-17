# Design Decisions

## Architecture Decisions

### Why Monolithic Over Microservices?
**Decision:** Single application with clear module separation

**Reasoning:**
- Simpler deployment for self-hosters
- Lower infrastructure requirements
- Easier debugging and development
- Most installations are single-user
- Can still scale vertically

**Trade-offs:**
- Harder to scale individual components
- All services restart together
- Language lock-in (Python + TypeScript)

**When to Reconsider:**
- Multi-tenant requirements
- Need independent scaling
- Team specialization by service

---

### Why SQLite Default Instead of PostgreSQL?
**Decision:** SQLite as default, PostgreSQL optional

**Reasoning:**
- Zero configuration for beginners
- Single file backup
- Sufficient for single-user workloads
- Easy migration to PostgreSQL later

**Trade-offs:**
- Concurrent write limitations
- No advanced features (full-text search, etc.)
- Database locking issues possible

**Migration Path:**
```python
# .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/audiovault
```

---

### Why FastAPI Over Flask/Django?
**Decision:** FastAPI as backend framework

**Reasoning:**
- Native async support (critical for downloads)
- Automatic API documentation (OpenAPI)
- Type safety with Pydantic
- Modern Python features (3.11+)
- Excellent performance
- WebSocket support built-in

**Trade-offs:**
- Less mature ecosystem than Flask
- Fewer third-party integrations
- Learning curve for async patterns

---

### Why yt-dlp Over Custom Downloaders?
**Decision:** yt-dlp as primary download engine

**Reasoning:**
- Supports 1000+ sites out of box
- Active maintenance and updates
- Battle-tested extraction logic
- Built-in proxy support
- Format selection and conversion
- Community-driven extractor fixes

**Trade-offs:**
- External dependency
- Breaking changes possible
- Limited control over extraction

**Fallback Strategy:**
- Platform-specific APIs as secondary
- Manual extraction for critical platforms

---

### Why React Query Over Redux?
**Decision:** React Query for state management

**Reasoning:**
- Server state is primary state type
- Automatic caching and invalidation
- Built-in loading/error states
- Less boilerplate than Redux
- Optimistic updates support

**Trade-offs:**
- Less suitable for complex client state
- Cache management complexity

**Complementary:**
- Context API for theme/auth
- Local state for UI-only state

---

## Feature Decisions

### Why Watchlist Auto-Sync?
**Decision:** Background job checks playlists every 60 minutes

**Reasoning:**
- Users want "set and forget" functionality
- Playlists change frequently on streaming platforms
- Reduces manual intervention

**Implementation:**
```python
# APScheduler job
@scheduler.scheduled_job('interval', minutes=60)
async def sync_watchlist():
    for item in watchlist:
        new_tracks = await fetch_new_tracks(item.url)
        await download_new_tracks(new_tracks)
```

**Safety Measures:**
- Dry-run mode
- User confirmation for deletions
- Rate limiting
- Error notifications

---

### Why Subsonic API?
**Decision:** Implement Subsonic v1.16.1 protocol

**Reasoning:**
- Wide ecosystem of mobile apps
- No need to build custom apps
- Standard protocol, well-documented
- Users already familiar with it

**Trade-offs:**
- Legacy protocol (XML-based)
- Some quirks (legacy auth required)
- Limited modern features

**Alternatives Considered:**
- Jellyfin API (too complex)
- Custom API (reinventing wheel)
- Plex API (proprietary)

---

### Why Fallback Download Strategy?
**Decision:** Multi-tier fallback system

**Reasoning:**
- Geo-restrictions common
- Platform links break frequently
- User expects "it just works"

**Tiers:**
1. Original URL with yt-dlp
2. Alternative search ("Official Audio", "Lyrics")
3. Cross-platform (try SoundCloud if YouTube fails)
4. Proxy services (Invidious for YouTube)

**Trade-offs:**
- More complex error handling
- Longer download times on failure
- Possible quality variations

---

## Security Decisions

### Why JWT Over Session Cookies?
**Decision:** JWT tokens for authentication

**Reasoning:**
- Stateless (no server-side session store)
- Works with mobile apps (Subsonic)
- CORS-friendly
- Scalable (no session affinity needed)

**Implementation:**
```python
from jose import jwt

token = jwt.encode(
    {"sub": user.id, "exp": datetime.utcnow() + timedelta(days=7)},
    SECRET_KEY,
    algorithm="HS256"
)
```

**Trade-offs:**
- Can't revoke tokens (until expiry)
- Token size larger than session ID
- Must handle refresh logic

**Mitigation:**
- Short expiration (7 days)
- Refresh token mechanism
- Logout clears client-side token

---

### Why No Built-In User Registration?
**Decision:** Admin creates users, no self-registration

**Reasoning:**
- Self-hosted (not SaaS)
- Prevents abuse
- Simpler security model
- Most installs are single-user

**Trade-offs:**
- Not suitable for public instances
- Admin must manage users

**Future:** Multi-tenant mode with registration

---

## Performance Decisions

### Why Redis Caching?
**Decision:** Optional Redis for caching

**Reasoning:**
- Reduce database load
- Fast API responses
- Cache expensive operations (metadata extraction)
- Session management

**What to Cache:**
- API responses (search results)
- Platform metadata
- User sessions
- Rate limit counters

**What NOT to Cache:**
- Download status (real-time)
- User preferences (small dataset)
- Authentication checks

---

### Why Async Throughout?
**Decision:** Async/await everywhere in backend

**Reasoning:**
- Non-blocking I/O critical for downloads
- Better resource utilization
- Handle multiple requests efficiently
- WebSocket support

**Challenges:**
- Learning curve
- Some libraries not async-compatible
- Debugging more complex

**Pattern:**
```python
# All DB operations
async def get_track(db: AsyncSession, track_id: int):
    result = await db.execute(select(Track).where(Track.id == track_id))
    return result.scalar_one_or_none()

# All HTTP calls
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

---

## UI/UX Decisions

### Why Glassmorphism Design?
**Decision:** Glass effect with backdrop blur

**Reasoning:**
- Modern, premium feel
- Distinguishes from other self-hosted apps
- Works well with music/audio theme
- Highlights content over chrome

**Implementation:**
```css
backdrop-filter: blur(12px);
background: rgba(255, 255, 255, 0.1);
border: 1px solid rgba(255, 255, 255, 0.2);
```

---

### Why Audio Visualizer?
**Decision:** Real-time frequency visualization

**Reasoning:**
- Enhances music listening experience
- Confirms audio is playing
- Visual feedback for quality
- Differentiates from basic players

**Technology:**
- Web Audio API
- Canvas rendering
- FFT analysis

**Trade-offs:**
- CPU usage
- Battery impact on mobile
- Not essential feature

---

## Testing Decisions

### Why pytest Over unittest?
**Decision:** pytest as testing framework

**Reasoning:**
- Cleaner syntax (no classes required)
- Better fixtures system
- Async support (pytest-asyncio)
- Rich plugin ecosystem
- Better error messages

---

### Why Integration Tests Focus?
**Decision:** More integration tests than unit tests

**Reasoning:**
- API contracts most important
- Database interactions critical
- End-to-end behavior matters

**Coverage Goals:**
- API endpoints: 95%+
- Business logic: 85%+
- UI components: 70%+

---

## Deployment Decisions

### Why Docker Compose Over Kubernetes?
**Decision:** Docker Compose as primary deployment

**Reasoning:**
- Self-hosted audience
- Single-server deployments
- Lower complexity
- Easier to debug
- Works on Unraid/TrueNAS

**When to Use Kubernetes:**
- Multi-server deployment
- High availability required
- Enterprise environment

---

### Why Multi-Stage Docker Builds?
**Decision:** Separate build and runtime stages

**Reasoning:**
- Smaller final images
- Faster deployments
- Security (no build tools in prod)

**Pattern:**
```dockerfile
# Build stage
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
CMD ["node", "dist/main.js"]
```
