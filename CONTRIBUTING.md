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

### Prerequisites

- Git
- Docker & Docker Compose

### Getting Started

```bash
# Fork and clone
git clone https://github.com/your-username/Audiovault.git
cd Audiovault
git remote add upstream https://github.com/Bl4nk44/Audiovault.git

# Configure environment
cp .env.example .env

# Start
docker compose up -d --build
```

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
