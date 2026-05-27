# Image-Based Delivery Design

**Date:** 2026-05-18  
**Status:** Approved  
**Scope:** Delivery pipeline for end-users of Audiovault (open-source distribution)

---

## Problem

Users clone the repo and get a `docker-compose.yml` with `build: context: .`. Every update requires `git pull` to get new code. Goal: `docker compose pull && docker compose up -d` is the only update command needed — no git interaction.

---

## Architecture

CI already builds and pushes images to Docker Hub on every push to `main` and `v*` tags. The missing piece is the server-side compose configuration.

### Image tags in use (CI, no changes needed)

| Tag | When pushed | Use case |
|-----|-------------|----------|
| `:latest` | Every push to `main` | User installs / updates |
| `:v1.2.3` | On `v*` tag | Pinned installs, rollback |
| `:main`, `:dev` | Branch push | Dev tracking |
| `:sha-xxxxxxx` | Every push | Audit / debug |

---

## Changes

### 1. `docker-compose.yml` — production (user-facing)

Remove all `build:` sections. Users never build locally.

Add `migrate` init-container that runs `alembic upgrade head` before backend starts.

```yaml
services:
  migrate:
    image: bl4nk404/audiovault:latest
    command: alembic upgrade head
    env_file: .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/audiovault
    depends_on:
      db:
        condition: service_healthy
    restart: "no"
    networks:
      - audiovault-network

  backend:
    image: bl4nk404/audiovault:latest
    depends_on:
      db:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully
    # ... rest unchanged

  frontend:
    image: bl4nk404/audiovault-frontend:latest
    # build: removed
    # ... rest unchanged
```

### 2. `docker-compose.dev.yml` — new file for developers

Override file with `build:` sections and code mounts for hot-reload.

Usage: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
      args:
        - APP_VERSION=dev
```

### 3. CI (`docker-build.yml`) — no changes

Already correct. Builds and pushes on `main` push and `v*` tags.

### 4. Documentation updates

- `QUICKSTART.md`: replace any `git pull` update instructions with `docker compose pull && docker compose up -d`
- `README.md`: same — update section about updating/upgrading
- Add developer note pointing to `docker-compose.dev.yml`

---

## User flows

### First install

```bash
git clone https://github.com/bl4nk44/Audiovault
cd Audiovault
cp .env.example .env
# edit .env
docker compose pull
docker compose up -d
```

### Every update

```bash
docker compose pull
docker compose up -d
```

Migrations run automatically via `migrate` init-container before backend starts.

### Developer workflow

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

---

## Migration behavior

`migrate` service is idempotent — `alembic upgrade head` is a no-op when schema is current. Safe to run on every `docker compose up -d`.

Dependency chain: `db healthy → migrate completes → backend starts`

---

## What we are NOT doing

- Watchtower — users can add it themselves if desired
- Versioned tags in compose — `:latest` sufficient for this use case
- `update.sh` script — two commands in README is enough
- Any changes to CI pipeline

---

## Verification

After implementation:

1. Fresh clone → `docker compose pull && docker compose up -d` → app running, migrations applied
2. Re-run `docker compose up -d` → migrate runs, no errors (idempotent)
3. Developer: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build` → hot-reload working
4. `docker-compose.yml` contains zero `build:` keys
