# Contributing to Audiovault

## Code of Conduct

This project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). Report unacceptable behavior to [bl4nk44@pm.me](mailto:bl4nk44@pm.me).

## How to Contribute

### Reporting Bugs

Use the [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md). Include:

- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Docker version)
- Logs from `docker compose logs backend` or browser console

### Suggesting Features

Use the [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.md) or start a [Discussion](https://github.com/Bl4nk44/Audiovault/discussions) first.

## Development Setup

### How it works

Audiovault ships two Docker Compose files:

| File | Purpose | Images |
|------|---------|--------|
| `docker-compose.yml` | Production / end-user deployment | Pre-built from Docker Hub |
| `docker-compose.dev.yml` | Development override | Built from local source |

The dev override changes two things: backend mounts `./backend` as a volume (uvicorn `--reload` watches for changes), and frontend uses `frontend/Dockerfile.dev` which runs the Vite dev server with hot module replacement.

### Ports

| Service | Dev mode | Prod mode |
|---------|----------|-----------|
| Frontend | `http://localhost:5173` (Vite) | `http://localhost:2137` (nginx) |
| Backend API | `http://localhost:8000` | `http://localhost:8000` |
| API docs | `http://localhost:8000/docs` | `http://localhost:8000/docs` |

### Prerequisites

- Git
- Docker & Docker Compose

### Getting Started (Docker — recommended)

```bash
# Fork and clone
git clone https://github.com/your-username/Audiovault.git
cd Audiovault
git remote add upstream https://github.com/Bl4nk44/Audiovault.git

# Configure environment
cp .env.example .env

# Build and start (dev mode — hot-reload enabled)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Frontend: http://localhost:5173
# Backend:  http://localhost:8000/docs
```

> **Note:** On the first run Docker builds both images from source, which takes a few minutes. Subsequent starts are fast unless you change `requirements.txt` or `package.json`.

### Getting Started (Native — without Docker)

Use this when you need faster iteration without Docker overhead or when debugging low-level issues. Requires PostgreSQL and Redis running separately (use the Docker services or your host installs).

**System requirements:**

| Dependency | Version | Notes |
|------------|---------|-------|
| Python | 3.14+ | pyenv recommended |
| Node.js | 24 LTS | nvm recommended |
| ffmpeg | any | `apt install ffmpeg` / `brew install ffmpeg` |
| aria2 | any | `apt install aria2` / `brew install aria2` |
| PostgreSQL | 16 | or use `docker compose up db -d` |
| Redis | 7+ | or use `docker compose up redis -d` |

**Backend:**

```bash
cd Audiovault

# Start only DB + Redis via Docker (skip if you have them locally)
docker compose up db redis -d

# Create virtualenv and install deps
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Configure environment (edit DATABASE_URL / REDIS_URL to point at localhost)
cp .env.example .env

# Run migrations
cd backend
alembic upgrade head

# Start dev server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**

```bash
cd Audiovault/frontend

npm ci
npm run dev
# http://localhost:5173
```

> **CORS:** In native mode the frontend runs on `http://localhost:5173`. Make sure your `.env` contains `BACKEND_CORS_ORIGINS=http://localhost:5173` (already set in `.env.example`).

### Pre-commit Hooks

```bash
pip install pre-commit
pre-commit run --all-files
```

> **Note**: `pre-commit install` conflicts with the global ggshield hook. Run manually or let CI handle it.

#### What Gets Checked

| Tool | Purpose | Scope |
|------|---------|-------|
| pre-commit-hooks | Trailing whitespace, YAML/JSON validation, merge conflicts | All |
| Ruff | Python linting + formatting | `backend/` |
| ggshield | Secret scanning | All |
| Semgrep | SAST (uses `.semgrep.yml`) | `backend/` |
| ESLint | TypeScript/React linting | `frontend/src/` |

### Backend Development

```bash
# Run tests (inside Docker)
docker compose exec backend pytest --cov=app

# Lint/format
ruff check backend/
ruff format backend/

# API docs
# http://localhost:8000/docs
```

### Frontend Development

```bash
# Run tests (inside Docker)
docker compose exec frontend npm test

# Lint
docker compose exec frontend npm run lint
```

## Git Workflow

### Branch Naming

```
feature/add-spotify-sync
fix/auth-token-refresh
docs/update-readme
refactor/simplify-api-calls
chore/update-dependencies
```

### Commit Messages

Conventional Commits format: `<type>(<scope>): <description>`

```
feat(spotify): add playlist import
fix(auth): resolve JWT expiration handling
docs: update installation guide
chore(deps): bump ruff to 0.15
```

Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `chore`, `ci`, `style`

### Pull Request Process

1. Rebase on upstream main: `git fetch upstream && git rebase upstream/main`
2. Push to your fork
3. Open a PR, fill out the template, link related issues with `Closes #N`
4. Address review comments — squash commits before merge

## Code Style

### Python

- Type hints required — use new syntax: `X | None`, `list[X]`
- No raw SQL — SQLAlchemy ORM only
- Async/await everywhere; no blocking I/O in async context
- Ruff handles formatting and linting (max line length: 120)

```python
async def get_track(track_id: int) -> Track | None:
    result = await db.execute(select(Track).where(Track.id == track_id))
    return result.scalar_one_or_none()
```

### TypeScript/React

- Strict TypeScript — no `any`
- Server state via TanStack Query, not `useEffect` + `useState`
- Tailwind CSS only — no inline styles, use `clsx` + `tailwind-merge`
- Named exports for components
- All UI strings go to `src/i18n/`

```typescript
interface TrackCardProps {
  trackId: string;
  onSelect: (id: string) => void;
}

export const TrackCard = ({ trackId, onSelect }: TrackCardProps) => (
  <div onClick={() => onSelect(trackId)}>{/* content */}</div>
);
```

## Testing

- Write tests for new features and bug fixes
- Target: ≥80% coverage for new code
- Backend uses SQLite + fakeredis in tests (not PostgreSQL)

```bash
# Backend
docker compose exec backend pytest --cov=app

# Frontend
docker compose exec frontend npm test -- --coverage
```

## Security

Found a vulnerability? Email [bl4nk44@pm.me](mailto:bl4nk44@pm.me) instead of opening an issue. See [SECURITY.md](SECURITY.md).

## Questions?

- [Discussions](https://github.com/Bl4nk44/Audiovault/discussions)
- [Issues](https://github.com/Bl4nk44/Audiovault/issues)
- [Wiki](https://github.com/Bl4nk44/Audiovault/wiki)
