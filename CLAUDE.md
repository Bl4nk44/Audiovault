# Audiovault

Self-hosted music library manager — import playlist z 7+ platform, download FLAC lokalnie.

## Stack
Backend: FastAPI + Python 3.14, SQLAlchemy 2.x async, Alembic, APScheduler, Redis
Frontend: React 19, TypeScript 5.9 strict, TailwindCSS v4, TanStack Query 5, Zustand 5
Deploy: Docker Compose — backend:8000, frontend:2137, db:5432, redis:6379

## Struktura
```
backend/app/
  api/routes/     ← tylko orchestracja, ZERO logiki biznesowej
  services/       ← cała logika biznesowa
  models/         ← SQLAlchemy ORM
  schemas/        ← Pydantic v2
  core/           ← config, security, deps, exceptions
  providers/      ← zewnętrzne API (Spotify, Deezer…)
frontend/src/
  api/ hooks/ store/ components/ pages/ types/ i18n/
```

## Komendy
```bash
docker compose up -d --build
docker compose exec backend pytest --cov=app --cov-report=term-missing
docker compose exec frontend npm test
cd backend && ruff check --fix . && ruff format .
alembic revision --autogenerate -m "opis" && alembic upgrade head
```

## Język
Kod / komentarze / commity / branche → English
UI tekst → Polish (i18n — nowe stringi w `frontend/src/i18n/`)

## Git
```
feat(scope): opis
fix(scope): opis
refactor/test/docs(scope): opis

Closes #nr
```

## Wzorce i konwencje (czytaj gdy kodujesz)
- `agent_docs/architecture.md` — system overview, warstwy, Subsonic API, Docker
- `agent_docs/testing.md` — fixtures, wzorce testów, uruchamianie, typowe błędy
- `agent_docs/patterns.md` — 10 wzorców kodu (async DB, service layer, yt-dlp, Pydantic v2…)
- `agent_docs/conventions.md` — Ruff, Pyright, Prettier, ESLint, HTTP codes, Glassmorphism
- `agent_docs/pitfalls.md` — pułapki, zależności do obserwowania

## Komendy projektu
- `/feature` — guided feature development workflow
- `/bugfix` — bug diagnosis and fix workflow
- `/review` — code review checklist
