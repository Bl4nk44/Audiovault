# Image-Based Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace local `--build` workflow with pre-built Docker Hub images so users update with `docker compose pull && docker compose up -d` — no `git pull` needed.

**Architecture:** `docker-compose.yml` becomes image-only (no `build:` keys) and gains a `migrate` init-container that runs `alembic upgrade head` before backend starts. A new `docker-compose.dev.yml` override restores `build:` sections and code mounts for developers. CI pipeline is unchanged.

**Tech Stack:** Docker Compose v2, Alembic, Docker Hub (`bl4nk404/audiovault:latest`, `bl4nk404/audiovault-frontend:latest`)

---

## File Map

| File | Action | What changes |
|------|--------|--------------|
| `docker-compose.yml` | Modify | Remove `build:` from backend + frontend; add `migrate` init-container; backend gets `depends_on: migrate` |
| `docker-compose.dev.yml` | Create | Override with `build:` + volume mounts for hot-reload |
| `QUICKSTART.md` | Modify | Replace `--build` start command; add Update section; add Developer section |
| `README.md` | Modify | Replace `--build` start command with `docker compose pull && up -d` |
| `CONTRIBUTING.md` | Modify | Replace `--build` with dev override command |

---

## Task 1: Remove `build:` from `docker-compose.yml`, add `migrate` init-container

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Open `docker-compose.yml` and locate the `backend` service**

Current state (lines to remove/change):
```yaml
backend:
  build:
    context: .
    dockerfile: backend/Dockerfile
  image: bl4nk404/audiovault:latest
```

- [ ] **Step 2: Replace the `backend` service block**

Remove `build:` entirely. Add `migrate` dependency. Final backend service top section:
```yaml
  backend:
    image: bl4nk404/audiovault:latest
    container_name: audiovault-backend
    restart: unless-stopped
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'
    ports:
      - "8000:8000"
      - "9900:9900"
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/audiovault
      - REDIS_URL=redis://redis:6379/0
      - ALLOWED_HOSTS=*
      - BACKEND_CORS_ORIGINS=${BACKEND_CORS_ORIGINS:-http://localhost:2137}
      - ENVIRONMENT=production
      - TIMEZONE=${TIMEZONE:-UTC}
      - TZ=${TIMEZONE:-UTC}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully
    networks:
      - audiovault-network
```

- [ ] **Step 3: Replace the `frontend` service block**

Remove `build:` and `args:` from frontend. Final:
```yaml
  frontend:
    image: bl4nk404/audiovault-frontend:latest
    container_name: audiovault-frontend
    restart: unless-stopped
    ports:
      - "2137:8080"
    depends_on:
      - backend
    networks:
      - audiovault-network
```

- [ ] **Step 4: Add `migrate` service before `backend` in the services block**

Insert after the `db` and `redis` services, before `backend`:
```yaml
  migrate:
    image: bl4nk404/audiovault:latest
    container_name: audiovault-migrate
    command: alembic upgrade head
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/audiovault
    depends_on:
      db:
        condition: service_healthy
    restart: "no"
    networks:
      - audiovault-network
```

- [ ] **Step 5: Verify no `build:` keys remain**

```bash
grep -n "build:" docker-compose.yml
```
Expected: no output (zero matches).

- [ ] **Step 6: Verify `migrate` service and dependency are present**

```bash
grep -n "migrate\|service_completed" docker-compose.yml
```
Expected: lines showing `migrate:` service and `service_completed_successfully`.

- [ ] **Step 7: Smoke-test compose file is valid YAML**

```bash
docker compose config --quiet
```
Expected: exit code 0, no errors.

- [ ] **Step 8: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(docker): switch to pre-built images, add migrate init-container"
```

---

## Task 2: Create `docker-compose.dev.yml` for developer builds

**Files:**
- Create: `docker-compose.dev.yml`

- [ ] **Step 1: Create the file**

```yaml
# Developer override — use with:
# docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    image: audiovault-backend-dev
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
      args:
        - APP_VERSION=dev
    image: audiovault-frontend-dev

  migrate:
    build:
      context: .
      dockerfile: backend/Dockerfile
    image: audiovault-backend-dev
```

- [ ] **Step 2: Verify override merges correctly**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
```
Expected: exit code 0. Backend service should show `build:` present and `image: audiovault-backend-dev`.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.dev.yml
git commit -m "feat(docker): add docker-compose.dev.yml override for local builds"
```

---

## Task 3: Update `QUICKSTART.md`

**Files:**
- Modify: `QUICKSTART.md`

- [ ] **Step 1: Replace `--build` start command in Step 3**

Find:
```
docker compose up -d --build
```
Replace with:
```
docker compose pull
docker compose up -d
```

- [ ] **Step 2: Add Update section after Step 4 (Access)**

Add a new `## Step 5: Updating` section:

```markdown
## Step 5: Updating

When a new version is released, pull the latest images and restart:

```bash
docker compose pull
docker compose up -d
```

Migrations run automatically. No `git pull` needed — unless you want to update `.env` with new config options.
```

- [ ] **Step 3: Add Developer section at the bottom (before the closing line)**

```markdown
## 🛠️ Developer Setup

To build images locally from source:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

This uses `docker-compose.dev.yml` which adds `build:` overrides and backend hot-reload.
```

- [ ] **Step 4: Verify the file has no remaining bare `--build` flags**

```bash
grep -n "\-\-build" QUICKSTART.md
```
Expected: only the developer section line (1 match).

- [ ] **Step 5: Commit**

```bash
git add QUICKSTART.md
git commit -m "docs(quickstart): replace --build with pull workflow, add update + dev sections"
```

---

## Task 4: Update `README.md`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Find the `--build` start command**

```bash
grep -n "\-\-build" README.md
```
Note the line number.

- [ ] **Step 2: Replace the start command**

Find (around line 101):
```
docker compose up -d --build
```
Replace with:
```
docker compose pull
docker compose up -d
```

- [ ] **Step 3: Verify**

```bash
grep -n "\-\-build" README.md
```
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): replace --build with pull workflow"
```

---

## Task 5: Update `CONTRIBUTING.md`

**Files:**
- Modify: `CONTRIBUTING.md`

- [ ] **Step 1: Find the `--build` reference**

```bash
grep -n "\-\-build" CONTRIBUTING.md
```
Note the line number (currently line 41).

- [ ] **Step 2: Replace with dev override command**

Find:
```
docker compose up -d --build
```
Replace with:
```
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

- [ ] **Step 3: Verify**

```bash
grep -n "docker compose" CONTRIBUTING.md
```
Expected: the dev override command is present.

- [ ] **Step 4: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs(contributing): update dev start command to use compose override"
```

---

## Task 6: End-to-end verification

- [ ] **Step 1: Confirm zero `build:` in production compose**

```bash
grep -c "build:" docker-compose.yml
```
Expected: `0`

- [ ] **Step 2: Confirm `migrate` init-container present and correct**

```bash
grep -A5 "migrate:" docker-compose.yml | head -20
```
Expected: shows `image:`, `command: alembic upgrade head`, `restart: "no"`.

- [ ] **Step 3: Confirm backend depends on migrate**

```bash
grep -A3 "service_completed_successfully" docker-compose.yml
```
Expected: present under `backend.depends_on`.

- [ ] **Step 4: Simulate user install (pull-only)**

```bash
docker compose pull 2>&1 | tail -5
```
Expected: images pulled from Docker Hub, no build errors. (Requires Docker Hub access and images to be present.)

- [ ] **Step 5: Validate dev override**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml config 2>&1 | grep -E "image:|build:" | head -10
```
Expected: `build:` present for backend/frontend/migrate, image names are `audiovault-backend-dev` / `audiovault-frontend-dev`.

- [ ] **Step 6: Final commit if any cleanup needed, then tag**

```bash
git log --oneline -6
```
All 5 commits from tasks 1-5 should be present.
