# AGENTS.md — Instrukcje dla Agentów AI (Audiovault)

## JĘZYK — POLSKI

**WAŻNE:** Odpowiadaj zawsze i wyłącznie po polsku. Nie używaj angielskiego chyba że:
- Cytujysz kod, nazwy zmiennych, lub commandy bash
- Odwołujesz się do nazw technologii (Python, FastAPI, Docker, itp.)
- Pytanie dotyczy dokładnej nazwy/części kodu

**Zasada:** Komentarze, wyjaśnienia, opisy, feedback — wszystko po polsku.

---

## Projekt

**Audiovault** to aplikacja do importowania, zarządzania i pobierania muzyki z różnych platform streamingowych (Spotify, YouTube, Deezer, SoundCloud, Apple Music, Tidal, Amazon Music) do lokalnego serwera. Aplikacja oferuje również serwer Subsonic API do strumieniowania muzyki.

**Stack technologiczny:**
- **Backend**: Python 3.13+, FastAPI, SQLAlchemy, Alembic, Redis, Socket.IO
- **Frontend**: React/TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand
- **Baza danych**: PostgreSQL (produkcja), SQLite (testy)
- **DevOps**: Docker Compose, GitHub Actions, SonarQube, Trivy, Semgrep
- **Testy**: pytest (≥80% coverage), React Testing Library, Vitest

**Architektura:**
```
backend/
├── app/
│   ├── api/          # Routy FastAPI (V1, Subsonic)
│   ├── models/       # Modele SQLAlchemy
│   ├── schemas/      # Pydantic v2 schemas
│   ├── services/     # Logika biznesowa (download, sync, lyrics, spotify, itp.)
│   ├── providers/    # Klienci API zewnętrznych platform (YouTube, Spotify, itp.)
│   ├── core/         # Konfiguracja, security, auth
│   └── main.py       # Aplikacja FastAPI + Socket.IO
├── tests/            # Testy (API, services, providers)
└── pyproject.toml    # Zależności Python (uv)

frontend/
├── src/
│   ├── components/   # Komponenty React
│   ├── hooks/        # Custom hooks (TanStack Query)
│   ├── store/        # Zustand stores
│   ├── api/          # Axios client
│   └── i18n/         # Tłumaczenia (polski)

docker-compose.yml    # Orkiestracja usług (backend, frontend, PostgreSQL, Redis, pgAdmin)
```

## Kontekst operacyjny

- **Środowisko**: Windows 11 + WSL2 (Kali Linux), Docker Desktop
- **GPU**: NVIDIA RTX 4080 + CUDA (dla możliwych przyszłych operacji na audio)
- **Repomix**: Używaj `repomix` do generowania skupionego kontekstu zamiast czytać wiele plików
- **OpenMemory**: Zachowuj kluczowe decyzje architektoniczne w pamięci cross-sesyjnej
- **Kompaktacja kontekstu**: Włączona — starsze wiadomości są automatycznie podsumowywane

## Active MCP Servers

- **semgrep** — SAST, analiza bezpieczeństwa kodu (użyj przed merge PR)
- **trivy** — skanowanie zależności, obrazów Docker, IaC
- **github** — GitHub API (PR, issues, pliki)
- **context7** — aktualna dokumentacja bibliotek (ZAWSZE przed użyciem nowej biblioteki)
- **sonarqube** — jakość kodu, coverage, security hotspots (project key: audiovault)
- **memory** — pamięć cross-sesyjna (wzorce, decyzje)
- **sequentialthinking** — złożona analiza problemów

## Zasady pracy

### 1. TDD (Test-Driven Development)
- **Najpierw test** (RED), potem implementacja (GREEN), potem refaktoring
- Minimalny kod przechodzący test → stopniowe ulepszanie
- Testy >= 80% coverage dla nowego kodu
- Testy jednostkowe dla logiki biznesowej w `backend/tests/`

### 2. Planowanie przed kodowaniem
- Przed dużymi zmianami stwórz `implementation_plan.md` w `/tmp/` lub w branchu
- Przed writing any code — przedstaw plan i czekaj na zatwierdzenie
- Duże zadania → podziel na osobne sesje (max 70% token limit per session)

### 3. Commity przyrostowe
- Jeden logical change = jeden commit
- Commit po każdym zielonym teście
- Używaj konwencji Conventional Commits: `feat(scope):`, `fix(scope):`, `chore(deps):`
- Branchy feature: `feature/nazwa`, bugfix: `fix/nazwa`

### 4. `/clear` po zakończeniu zadania

### 5. Przed akcją: "czy muszę czytać cały plik?" — użyj grep/seek najpierw

## Stack-Specific Rules

### Backend (Python/FastAPI)

- **Async/await** — wszędzie. Żadnych blokujących wywołań I/O w async context
- **Type hints** — obowiązkowe na wszystkich funkcjach (nowy syntax: `X | None`, `list[X]`, nie `Optional[X]`)
- **Logika biznesowa** — w `services/`, NIGDY w routerach
- **SQLAlchemy** — ORM zawsze, żadnych raw SQL concatenation
- **Pydantic v2** — `model_config = ConfigDict(from_attributes=True)`, nie `class Config`
- **N+1 queries** — używaj `selectinload()` dla relationships
- **yt-dlp** — zawsze w `asyncio.to_thread()`, nigdy bezpośrednio w async
- **HTTP zewnętrzny** — `aiohttp`, nigdy `requests`
- **Custom exceptions** — subklasy `AudiovaultException`, nie `Exception`
- **HTTP status codes**: `201` create, `204` delete, `401` unauth, `404` not found, `422` validation error
- **Alembic migration** — obowiązkowy dla każdej zmiany modelu: `alembic revision --autogenerate -m "..."`

### Frontend (TypeScript/React)

- **TypeScript strict mode** — żadnego `any`. Używaj `unknown` jeśli nie wiesz.
- **TanStack Query** — dla server state (żadnych manualnych `useEffect` + `useState` do API calls)
- **Zustand** — tylko dla client state (theme, auth, UI). NIE dla danych z serwera.
- **`queryClient.invalidateQueries()`** — po każdej mutacji (create/update/delete)
- **TailwindCSS** — wyłącznie. Żadnych inline styles.
- **Conditional classes** — `tailwind-merge` + `clsx`
- **Performance** — `React.memo` / `useMemo` dla kosztownych list
- **Named exports** — dla komponentów
- **Socket.IO** — handler zdarzeń (nie raw WebSocket)
- **Responsywność** — mobile-first, dostępność (a11y)

### Security

- **Żadnych hardcoded secrets** — env vars tylko (`.env` nie commitowane!)
- **Walidacja inputu** — Pydantic (backend) / TypeScript (frontend)
- **JWT validation** — na protected routes
- **Sensitive data** — żadnych w logach ani Socket.IO payloads

### Testing & Quality

- **pytest** — backend testy, asyncio support
- **Coverage ≥ 80%** — nowe funkcje
- **Ruff** — linting i formatting: `ruff check .`, `ruff format .`
- **Mypy** — type checking (jeśli używasz)
- **Frontend tests** — Vitest + React Testing Library

## Workflow — Typowe Zadania

### Bugfix (użyj `/bugfix` lub read `.kilo/commands/bugfix.md`)

1. Reprodukuj: `docker compose logs backend | grep ERROR`, `pytest tests/path/test.py -v --tb=long`
2. Diagnozuj: izoluj warstwę (service/route/provider/DB)
3. **Najpierw test reprodukujący** (RED → GREEN)
4. Napraw w właściwej warstwie
5. `docker compose exec backend pytest --cov=app` — brak regresji
6. Commit: `fix(scope): opis — fixes #nr`

### Nowy Feature (użyj `/feature`)

1. Plan — przedstaw architekturę, zmiany w każdym warstwowym
2. Backend order: schemas → models+migration → providers → services → routes → tests
3. Frontend order: types → api client → hooks → store → components → pages → tests
4. Commit: `feat(scope): opis`

### Code Review (użyj `/review`)

- Sprawdź checklistę w `.kilo/commands/review.md`
- `semgrep scan` na zmienionych plikach
- Pokrycie testów ≥80%
- Brak logiki biznesowej w routerach

## MCP & CLI Tools — Kiedy używać

| Tool | Kiedy używać | Przykład |
|------|--------------|----------|
| `semgrep_scan` | Przed PR merge, nowe endpointy | `semgrep_scan --include backend/app/services/` |
| `trivy_scan_filesystem` | Przed release, security audit | `trivy scan_filesystem --skip-dirs node_modules,.venv` |
| `github_create_pull_request` | Feature skończony, testy zielone | — |
| `context7` | PRZED użyciem nieznanej biblioteki | `resolve-library-id` + `get-library-docs` |
| `repomix` | Zamiast czytać 10+ plików — bundluj obszar | `repomix --include "backend/app/services/download*,backend/tests/services/test_download*" --style xml` |

## Środowisko i narzędzia

- **Python**: 3.13.x, `uv` jako menadżer pakietów (`uv pip install`, `uv pip list`)
- **Node.js**: v25.x (nvm), `npm` lub `pnpm`
- **Docker**: Docker Compose v5+, kontenery: `backend`, `frontend`, `postgres`, `redis`, `pgadmin`
- **Testy**: `docker compose exec backend pytest` lub lokalnie `pytest tests/ -v`
- **Linting**: `ruff check .`, `ruff format .` (backend), `npm run lint` (frontend)
- **Migrations**: `docker compose exec backend alembic upgrade head`

**Ścieżki kluczowe:**
- Backend kod: `backend/app/`
- Frontend kod: `frontend/src/`
- Testy: `backend/tests/`
- Docker: `docker-compose.yml`, `docker/`
- Konfiguracja: `.env`, `backend/app/core/config.py`

## Przestrzeń nazw i konwencje

- **Python**: snake_case dla funkcji/promieni, PascalCase dla klas, moduły lowercase
- **TypeScript**: camelCase dla zmiennych/funkcji, PascalCase dla komponentów/interfejsów
- **Commit messages**: `feat(scope):`, `fix(scope):`, `chore(deps):`, `docs:`, `refactor:`
- **Branchy**: `feature/`, `fix/`, `chore/`, `docs/`

##可用ne Agenci Kilo Code

- **senior-developer** (domyślny) — TDD-first, cyniczny, polski, najlepsze praktyki
- **code-reviewer** — przegląd kodu przed merge
- **frontend-specialist** — React/TS/UX
- **test-engineer** — testy, coverage, debugging
- **docs-specialist** — dokumentacja

## Ważne pliki projektu

- `README.md` — overview, quickstart
- `QUICKSTART.md` — szybki start
- `CONTRIBUTING.md` — contribution guidelines
- `CHANGELOG.md` — historia zmian
- `docs/` — szczegółowa dokumentacja (platform support, automation, audio quality, streaming)
- `backend/app/core/config.py` — konfiguracja aplikacji (env vars)
- `pyproject.toml` — Python dependencies
- `docker-compose.yml` — usługi Docker

## Bezpieczeństwo — zawsze

1. **Secrets**: sprawdź `ggshield secret scan path .` przed commitem nowego kodu auth
2. **Dependencies**: `trivy scan_filesystem` i `semgrep scan` przed PR
3. **Docker**: nie używaj `root` w Dockerfile, non-root user
4. **Env vars**: `.env` w `.gitignore`, przykład w `.env.example`

## OpenMemory — sektory

Zapisuj informacje do odpowiednich sektorów:

| Sektor | Kiedy używać | Przykład |
|--------|--------------|----------|
| `semantic` | Fakty, architektura, konfiguracja | "Backend używa FastAPI z Socket.IO" |
| `episodic` | Zdarzenia, zmiany, migracje | "2026-04-23: Dodano Spotify fallback mechanism" |
| `procedural` | Wzorce, procesy, komendy | "Workflow bugfix: reproduce → diagnose → test → fix" |
| `emotional` | Preferencje użytkownika, style | "Użytkownik preferuje FLAC quality" |
| `reflective` | Wnioski, lessons learned | "yt-dlp wymaga asyncio.to_thread w FastAPI" |

## Workflows dostępne jako slash commands

- `/bugfix` — diagnostyka i naprawa buga ( workflow: reproduce → diagnose → test → fix)
- `/feature` — implementacja nowego feature (plan → backend → frontend → tests)
- `/review` — code review przed PR merge (checklisty backend/frontend/security)

Workflow files are located in `.kilo/commands/`.

## Troubleshooting

**Testy nie przechodzą?**
- `docker compose logs backend` — sprawdź błędy
- `pytest tests/path/test.py::test_name -v --tb=long` — pełny traceback
- `ruff check .` — lint errors

**Frontend nie kompiluje?**
- `npm run lint` — ESLint errors
- `npm run build` — build errors
- Sprawdź `import` paths, `tsconfig.json` aliases

**Docker issues?**
- `docker compose ps` — status kontenerów
- `docker compose logs frontend` — frontend logs
- `docker compose down && docker compose up -d --build` — restart

