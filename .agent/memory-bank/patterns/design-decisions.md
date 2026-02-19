# Design Decisions

## Architecture

### Monolithic over Microservices
**Decision:** Single app z separacją modułów
**Reasoning:** Prostsze deploy dla self-hosterów, mniejsze wymagania infra, łatwiejszy debug, większość instalacji single-user
**Trade-offs:** Trudniejsze skalowanie komponentów, restart wszystkiego naraz
**Reconsider when:** Multi-tenant, niezależne skalowanie, team specialization

### SQLite default, PostgreSQL optional
**Decision:** Zero-config dla beginnerów, single-file backup, wystarczający dla single-user
**Trade-offs:** Concurrent write limits, brak advanced features, możliwe locking
**Migration:** `DATABASE_URL=postgresql+asyncpg://user:pass@localhost/audiovault`

### FastAPI over Flask/Django
**Decision:** Native async (krytyczne dla downloadsów), auto OpenAPI docs, Pydantic type safety, WebSocket built-in
**Trade-offs:** Mniej dojrzały ekosystem niż Flask, learning curve dla async

### yt-dlp over custom downloaders
**Decision:** 1000+ supported sites, aktywny maintenance, battle-tested, proxy support
**Trade-offs:** External dependency, możliwe breaking changes
**Fallback:** Platform-specific APIs jako secondary

### React Query over Redux
**Decision:** Server state jest primary — auto caching/invalidation, mniej boilerplate
**Trade-offs:** Mniej odpowiedni dla complex client state
**Complementary:** Context API (theme/auth), local state (UI-only)

## Features

### Watchlist Auto-Sync (60min interval)
**Reasoning:** Set-and-forget UX, playlisty często się zmieniają
**Safety:** dry-run mode, user confirmation dla deletions, rate limiting

### Subsonic API v1.16.1
**Reasoning:** Szeroki ekosystem mobilnych apps, brak potrzeby budowania własnych, użytkownicy już znają
**Trade-offs:** Legacy XML protocol, quirky auth, limited modern features

### Multi-tier Fallback Download
**Tiers:** Original URL → Alternative queries → Cross-platform → Invidious proxy
**Trade-offs:** Bardziej złożona obsługa błędów, dłuższy czas przy failure, możliwe różnice jakości

### JWT over Session Cookies
**Reasoning:** Stateless (no server session store), działa z mobile apps, CORS-friendly
**Trade-offs:** Nie można revokować przed expiry (mitigacja: 7d expiry + refresh tokens)

### No Self-Registration
**Reasoning:** Self-hosted (nie SaaS), zapobiega abuse, prostszy security model
**Future:** Multi-tenant mode z rejestracją

### Docker Compose over Kubernetes
**Reasoning:** Self-hosted audience, single-server deployment, działa na Unraid/TrueNAS
**When K8s:** Multi-server, high availability, enterprise

### Glassmorphism UI
**Reasoning:** Modern/premium feel, wyróżnia się wśród self-hosted apps, pasuje do muzycznego tematu
**Implementation:** `backdrop-filter: blur(12px)`, `background: rgba(255,255,255,0.1)`

### pytest over unittest
**Reasoning:** Czystszy syntax, lepszy fixtures system, async support, rich plugin ecosystem
**Coverage goals:** API endpoints 95%+, business logic 85%+, UI components 70%+
