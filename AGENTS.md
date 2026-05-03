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
- **Backend**: Python 3.14 (Docker `python:3.14-slim-bookworm`), FastAPI, SQLAlchemy, Alembic, Redis, Socket.IO, APScheduler
- **Frontend**: React 18/TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand
- **Baza danych**: PostgreSQL 16 (produkcja), SQLite + aiosqlite (testy)
- **DevOps**: Docker Compose, GitHub Actions, SonarQube, Trivy, Semgrep
- **Testy**: pytest + pytest-asyncio + fakeredis (≥80% coverage), React Testing Library, Vitest

**Architektura:**
```
backend/
├── app/
│   ├── api/v1/       # Routy FastAPI (jeden plik na platformę + auth/users/settings/sync)
│   ├── api/subsonic/ # Subsonic API (zgodność z Symfonium/Amperfy/DSub)
│   ├── models/       # Modele SQLAlchemy (async)
│   ├── schemas/      # Pydantic v2 schemas
│   ├── services/     # Logika biznesowa (download_manager, sync_manager, scheduler, per-platforma)
│   ├── providers/    # Async aiohttp klienci platform (base.py + per-platforma)
│   ├── core/         # config.py (pydantic-settings), security.py (JWT), auth
│   └── main.py       # Aplikacja FastAPI + Socket.IO
├── tests/            # Testy (API, services, providers)
└── requirements.txt  # Zależności Python (pip)

frontend/
├── src/
│   ├── components/   # Komponenty React (glassmorphism theme)
│   ├── hooks/        # Custom hooks (TanStack Query)
│   ├── store/        # Zustand stores (tylko client-state)
│   ├── api/          # Axios client
│   └── i18n/         # Tłumaczenia (wyłącznie polski)

docker-compose.yml    # Orkiestracja usług: backend, frontend, PostgreSQL 16, Redis 8
```

## Kontekst operacyjny

- **Środowisko**: Ubuntu 24.04 LTS w WSL2 (Windows host), Docker Desktop
- **GPU**: NVIDIA RTX 4080 + CUDA (dla możliwych przyszłych operacji na audio)
- **Repomix**: Używaj `repomix --compress` do generowania skupionego kontekstu zamiast czytać wiele plików
- **Memory MCP**: Zachowuj kluczowe decyzje architektoniczne w pamięci cross-sesyjnej
- **Kompaktacja kontekstu**: Włączona — starsze wiadomości są automatycznie podsumowywane

## Narzędzia — Pełna Referencja

### Serwery MCP (przez MetaMCP `http://localhost:12008`)

> Sprawdź dostępność: `/mcp-status`. Wszystkie serwery przez jeden endpoint — MetaMCP jako proxy.

#### SAST i Code Security

| Serwer | Kluczowe funkcje MCP | Kiedy używać w Audiovault |
|--------|---------------------|--------------------------|
| **Semgrep** | `semgrep_scan` | SAST na nowym kodzie. Reguły w `.semgrep.yml` (custom: SQL injection, path traversal, JWT, XSS). Uruchamiaj po każdym nowym endpoincie lub serwisie. |
| **Snyk** | `snyk_code_scan`, `snyk_test`, `snyk_monitor` | Snyk At Inception — po każdej nowej funkcji. `snyk_test` na `requirements.txt` i `package.json` przed commitem zmiany deps. `snyk_code_scan` wykrywa insecure patterns w FastAPI/React. |
| **SonarQube** | `sonarqube_search_issues`, `sonarqube_get_metrics`, `sonarqube_get_quality_gate` | Trendy jakości, security hotspots, coverage delta. Project key: `audiovault`. Uruchom lokalnie: `http://localhost:9000`. |
| **Socket.dev** | `socket_scan_npm`, `socket_scan_pypi` | **PRZED** `npm install` lub `pip install` nowej paczki — supply chain attack detection. Szczególnie ważne przy dodawaniu dostawców audio. |

#### Dependency & Infrastructure Scanning

| Serwer | Kluczowe funkcje MCP | Kiedy używać w Audiovault |
|--------|---------------------|--------------------------|
| **Snyk** (deps) | `snyk_test` | `requirements.txt` + `frontend/package.json` — CVE w zależnościach. Przed każdym PR z `chore(deps)`. |
| **OSV-Scanner** | `osv_scan_directory`, `osv_scan_sbom` | Google CVE DB — wolniejszy od Snyk, ale inne źródło. Używaj jako second opinion przy HIGH/CRITICAL. |
| **Trivy** (v0.70.0) | `trivy_scan_filesystem`, `trivy_scan_image` | Skanowanie obrazu `bl4nk404/audiovault:latest` przed release. Filesystem scan: `backend/`, `frontend/` + IaC (Dockerfile, docker-compose.yml). |
| **Nuclei** (v3.x) | `nuclei_scan` | DAST — skanuje działającą aplikację pod `http://localhost:8000` i `http://localhost:2137`. Uruchamiaj gdy backend działa lokalnie. Templates: CVE, exposed-panels, misconfigurations. |

#### Dokumentacja i Research

| Serwer | Kluczowe funkcje MCP | Kiedy używać w Audiovault |
|--------|---------------------|--------------------------|
| **Context7** | `resolve-library-id`, `get-library-docs` | **ZAWSZE** przed użyciem nowej biblioteki lub nieznanej metody. Pobiera aktualną dokumentację (FastAPI, SQLAlchemy, TanStack Query, yt-dlp, aiohttp, Pydantic v2, Alembic). Przykład: `resolve-library-id("fastapi")` → `get-library-docs(id, topic="dependencies")`. |
| **Brave Search** | `brave_web_search`, `brave_local_search` | Szukanie rozwiązań bugów yt-dlp, sprawdzanie czy platforma zmieniła API, researching streaming service endpoints. 2000 req/miesiąc free. |
| **Sentry** | `get_sentry_issue`, `list_sentry_issues`, `get_sentry_event` | Stack traces z produkcji. Gdy bug jest zgłoszony przez usera — zanim zaczniesz debug, sprawdź czy Sentry ma event z dokładnym traceback. |

#### Automatyzacja i Workflow

| Serwer | Kluczowe funkcje MCP | Kiedy używać w Audiovault |
|--------|---------------------|--------------------------|
| **GitHub** | `create_pull_request`, `get_file_contents`, `create_issue`, `list_pull_requests`, `search_code`, `push_files`, `create_or_update_file` | PR creation po ukończeniu feature/fix. `search_code` do znalezienia wzorców w repo. `create_issue` do dokumentowania znalezionych bugów podczas pracy. |
| **Playwright** | `browser_navigate`, `browser_screenshot`, `browser_click`, `browser_type`, `browser_evaluate` | E2E testy UI — weryfikacja downloadu, importu playlist, Subsonic API. Uruchamiaj na `http://localhost:2137`. Szczególnie użyteczny dla kompleksowych flow (login → import → download). |
| **Sequential Thinking** | `sequentialthinking` | Złożone problemy wieloetapowe: architektura nowej platformy, debugowanie race condition, refaktor download pipeline. Gdy problem wymaga >5 kroków logicznego rozumowania. |

#### Pamięć i Stan

| Serwer | Kluczowe funkcje MCP | Kiedy używać w Audiovault |
|--------|---------------------|--------------------------|
| **Memory** | `create_entities`, `add_observations`, `search_nodes`, `open_nodes`, `read_graph`, `delete_entities` | Cross-sesyjna pamięć. Zapisuj: decyzje architektoniczne, nauczone wzorce (np. "yt-dlp wymaga to_thread w FastAPI"), znane konfiguracje platform, preferencje projektu. Szukaj: `search_nodes("download pipeline")`. |
| **Voice Mode** | `mcp__voice-mode__converse`, `mcp__voice-mode__service` | STT/TTS przez Whisper. Host bezpośrednio (nie przez MetaMCP). Wymaga PulseAudio (`RDPSource` jako default-source). Używaj do voice-driven coding gdy masz ręce zajęte. |

---

### CLI Narzędzia — Pełna Referencja

#### SAST / Secret Scanning (lokalny stack)

| Narzędzie | Wersja | Główne komendy dla Audiovault |
|-----------|--------|-------------------------------|
| **Semgrep** | 1.161.0 | `semgrep --config=.semgrep.yml backend/app/` — używa projektu `.semgrep.yml` z custom rules (FastAPI rate-limit, SQL injection, JWT). `semgrep --config=auto` dla pełnego skanu reguł publicznych. |
| **ggshield** | 1.50.2 | `ggshield secret scan path .` — wykrywa tokeny, klucze API, hasła w kodzie. Działa automatycznie przy `git commit` przez globalny hook `core.hooksPath`. |
| **Checkov** | 3.2.526 | `checkov -f docker-compose.yml` — IaC: wykrywa `privileged: true`, brak healthcheck, root user w Dockerfile. `checkov -d .` dla pełnego skanu. |
| **Snyk CLI** | 1.1304.1 | `snyk test --file=backend/requirements.txt` — CVE w Python deps. `snyk test --file=frontend/package.json` — npm deps. `snyk code test backend/` — SAST. |

#### Dependency Scanning

| Narzędzie | Wersja | Główne komendy dla Audiovault |
|-----------|--------|-------------------------------|
| **OSV-Scanner** | 2.3.5 | `osv-scanner scan --recursive .` — Google CVE DB dla Python i npm. `osv-scanner scan --lockfile=backend/requirements.txt` — tylko Python. |
| **Trivy** | 0.70.0 | `trivy fs --skip-dirs node_modules,.venv,dist backend/ frontend/` — filesystem. `trivy image bl4nk404/audiovault:latest` — Docker image scan przed release. `trivy config docker-compose.yml` — IaC misconfigs. |
| **Nuclei** | 3.x | `nuclei -u http://localhost:8000 -t cves/ -t exposures/` — wymaga działającego backendu. `nuclei -u http://localhost:2137 -t technologies/ -t misconfigurations/` — frontend. |

#### Code Quality

| Narzędzie | Główne komendy dla Audiovault |
|-----------|-------------------------------|
| **ruff** | `ruff check backend/` — linting (E/F/W/S/B/I/UP/N, config: `pyproject.toml`). `ruff format backend/` — formatting. `ruff check --fix backend/` — auto-fix. |
| **ESLint** | `npm run lint` z `frontend/` — flat config z security+sonarjs+no-unsanitized. `npm run lint -- --fix` — auto-fix. |
| **pre-commit** | `pre-commit run --all-files` — pełny pipeline (ruff → ggshield → semgrep → eslint). `pre-commit run --files backend/app/services/download_manager.py` — wybrany plik. |

#### GitHub i Playwright CLI

| Narzędzie | Wersja | Główne komendy dla Audiovault |
|-----------|--------|-------------------------------|
| **GitHub CLI** (`gh`) | 2.92.0 | `gh pr create --title "feat(x): ..."` — nowy PR. `gh pr list` — lista PR. `gh issue create` — nowy issue. `gh pr checks` — status CI. `gh run list` — lista GitHub Actions runs. |
| **Playwright** | via npm | `npx playwright test` — E2E testy (jeśli skonfigurowane). `npx playwright codegen http://localhost:2137` — record test przez nagrywanie akcji w UI. |

---

### Optymalizacja tokenów

| Narzędzie | Jak działa | Użycie |
|-----------|-----------|--------|
| **repomix** | Kompresuje cały repo do XML (~70% redukcja). Projekt ma `repomix.config.json` — wyklucza 112 `.cover` plików. Pełne repo: 498 plików / ~201K tokenów. | `repomix -o /tmp/ctx.xml .` — pełny kontekst. `repomix --compress --include "backend/app/services/**" -o /tmp/ctx.xml .` — fokus. |
| **RTK** (Rust Token Killer) | Hook `PreToolUse Bash → rtk hook claude` w `~/.claude/settings.json`. Filtruje i kompresuje output każdej komendy bash zanim trafi do Claude. ~60-90% oszczędności na `ls`, `git`, `cat`. | `rtk gain` — statystyki sesji. `rtk gain --history` — historia. `rtk discover` — co jeszcze można optymalizować. |
| **Caveman** (plugin Claude Code) | Aktywny plugin kompresujący output narzędzi Claude. ~65% mniejszy output. Działa automatycznie — nie wymaga konfiguracji. | Automatyczny. Brak ręcznej obsługi. |
| **ccusage** | Monitoruje zużycie tokenów Pro plan (okno 5h). Uruchom w bocznym terminalu. | `npx ccusage@latest blocks --live` — live monitoring. Gdy >70% okna: `/compact-smart`. |

#### Kiedy używać co

```
Analizujesz >5 plików         → repomix (agent repomix-analyzer)
Chcesz wiedzieć ile spaliłeś  → rtk gain + npx ccusage blocks --live
Długa sesja, zmiana tematu    → /compact (zachowaj kontekst) lub /clear (nowe zadanie)
Przed commitem                → pre-commit run --files <changed>
Nowa paczka npm/pip           → Socket.dev MCP PRZED instalacją
Przed PR                      → /sec-scan (semgrep + snyk + trivy)
Niezna biblioteka             → context7 resolve-library-id PRZED napisaniem kodu
Bug w produkcji               → Sentry MCP (stack trace) PRZED debugowaniem lokalnie
```

## Zasady pracy

### 1. TDD (Test-Driven Development)
- **Najpierw test** (RED), potem implementacja (GREEN), potem refaktoring
- Minimalny kod przechodzący test → stopniowe ulepszanie
- Testy >= 80% coverage dla nowego kodu
- Testy jednostkowe dla logiki biznesowej w `backend/tests/`

### 2. Planowanie przed kodowaniem
- Przed dużymi zmianami przedstaw plan i czekaj na zatwierdzenie
- Duże zadania → podziel na osobne sesje

### 3. Commity przyrostowe
- Jeden logical change = jeden commit
- Używaj konwencji Conventional Commits: `feat(scope):`, `fix(scope):`, `chore(deps):`
- Branchy feature: `feature/nazwa`, bugfix: `fix/nazwa`

### 4. Przed akcją: "czy muszę czytać cały plik?" — użyj grep/seek najpierw

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
- **i18n** — nowe stringi UI tylko do `frontend/src/i18n/` (wyłącznie polski)

### Security

- **Żadnych hardcoded secrets** — env vars tylko (`.env` nie commitowane!)
- **Walidacja inputu** — Pydantic (backend) / TypeScript (frontend)
- **JWT validation** — na protected routes
- **Sensitive data** — żadnych w logach ani Socket.IO payloads

### Testing & Quality

- **pytest** — backend testy, asyncio_mode=auto, SQLite+fakeredis in-memory
- **Coverage ≥ 80%** — nowe funkcje
- **Ruff** — linting i formatting: `ruff check .`, `ruff format .` (config w `pyproject.toml`)
- **ESLint** — `npm run lint` (frontend, flat config z security+sonarjs)
- **Frontend tests** — Vitest + React Testing Library

## Workflow — Typowe Zadania

### Bugfix (użyj `/bugfix`)

1. Reprodukuj: `docker compose logs backend | grep ERROR`, `pytest tests/path/test.py -v --tb=long`
2. Diagnozuj: izoluj warstwę (service/route/provider/DB)
3. **Najpierw test reprodukujący** (RED → GREEN)
4. Napraw w właściwej warstwie
5. `docker compose exec backend pytest --cov=app` — brak regresji
6. Commit: `fix(scope): opis — fixes #nr`

### Nowy Feature (użyj `/feature`)

1. Plan — przedstaw architekturę, zmiany w każdej warstwie
2. Backend order: schemas → models+migration → providers → services → routes → tests
3. Frontend order: types → api client → hooks → store → components → pages → tests
4. Commit: `feat(scope): opis`

### Code Review (użyj `/review`)

- Sprawdź checklistę w `.claude/commands/review.md`
- `semgrep scan` na zmienionych plikach
- Pokrycie testów ≥80%
- Brak logiki biznesowej w routerach

## Środowisko i narzędzia

- **Python**: 3.14 (Docker), zależności przez `pip` / `requirements.txt`
- **Node.js**: 24 LTS (nvm), `npm`
- **Docker**: kontenery: `backend` (port 8000), `frontend` (port 2137), `db` (PostgreSQL 16), `redis`
- **Testy**: `docker compose exec backend pytest` lub lokalnie `pytest backend/tests/ -v`
- **Linting**: `ruff check .` + `ruff format .` (backend), `npm run lint` (frontend)
- **Migrations**: `docker compose exec backend alembic upgrade head`

**Porty:** Frontend `http://localhost:2137` | Backend API `http://localhost:8000/docs`

### Repomix — kontekst repo dla Claude

Projekt ma `repomix.config.json` (wyklucza 112 plików `.cover` i innych artefaktów).
Pełne repo: **498 plików / ~201K tokenów** (skompresowane, bez konfigu byłoby 331K).

```bash
# Pełny kontekst
repomix -o /tmp/ctx.xml .

# Fokus — ZAWSZE preferuj zamiast czytania 10+ plików ręcznie
repomix --compress --include "backend/app/services/download_manager*,backend/tests/services/test_download*" -o /tmp/ctx.xml .
```

Dla zadań obejmujących >5 plików użyj subagenta `repomix-analyzer`:
```
Agent(subagent_type="repomix-analyzer", prompt="Przeanalizuj ...")
```

### RTK — kompresja outputu bash

RTK v0.38.0 skonfigurowany jako `PreToolUse Bash` hook w `~/.claude/settings.json`.
Automatycznie kompresuje output każdego polecenia bash przed wysłaniem do Claude (~60-90% mniej tokenów).

```bash
rtk gain            # statystyki oszczędności tokenów bieżącej sesji
rtk gain --history  # historia komend
rtk discover        # sugestie nieużywanych możliwości RTK
```

**Ścieżki kluczowe:**
- Backend kod: `backend/app/`
- Frontend kod: `frontend/src/`
- Testy: `backend/tests/`
- Konfiguracja: `.env`, `backend/app/core/config.py`
- Slash commands: `.claude/commands/` (`/bugfix`, `/feature`, `/review`, `/db-migrate`, `/docker-up`)

## Dostępne slash commands i agenty (Claude Code)

### Slash commands (`.claude/commands/`)
- `/bugfix` — diagnostyka i naprawa buga (reproduce → diagnose → test → fix)
- `/feature` — implementacja nowego feature (plan → backend → frontend → tests)
- `/review` — code review przed PR merge (checklisty backend/frontend/security)
- `/db-migrate` — tworzenie i aplikowanie migracji Alembic
- `/docker-up` — zarządzanie środowiskiem Docker Compose
- `/coverage` — pytest z raportem pokrycia + wskazanie niepokrytych linii
- `/check-types` — pyright + mypy (backend) + tsc (frontend) w jednym przebiegu

### Subagenty projektu (`.claude/agents/`) — działają w izolowanym kontekście
- `platform-integrator` — dodaje nową platformę streamingową end-to-end (provider + service + route + testy)
- `download-debugger` — diagnozuje błędy download pipeline (async, yt-dlp, Socket.IO, fallback)

### Subagenty globalne (`~/.claude/agents/`)
- `security-reviewer` — semgrep + ggshield + checkov + Snyk na zmienionych plikach
- `test-writer` — TDD: failing test przed implementacją (RED-GREEN-REFACTOR)
- `repomix-analyzer` — analiza >5 plików przez repomix w izolowanym kontekście

### Globalne slash commands
- `/sec-scan` — pełny pipeline security (lokalny stack + MCP)
- `/compact-smart` — sprawdza burn rate, rekomenduje /compact
- `/tokens` — status zużycia tokenów Pro plan + RTK gain
- `/ship` — pre-merge workflow (security + testy + PR)

## Przestrzeń nazw i konwencje

- **Python**: snake_case dla funkcji/zmiennych, PascalCase dla klas, moduły lowercase
- **TypeScript**: camelCase dla zmiennych/funkcji, PascalCase dla komponentów/interfejsów
- **Commit messages**: `feat(scope):`, `fix(scope):`, `chore(deps):`, `docs:`, `refactor:`
- **Branchy**: `feature/`, `fix/`, `chore/`, `docs/`

## Ważne pliki projektu

- `README.md` — overview, quickstart
- `QUICKSTART.md` — szybki start
- `CONTRIBUTING.md` — contribution guidelines
- `CHANGELOG.md` — historia zmian
- `docs/` — szczegółowa dokumentacja (platform support, automation, audio quality, streaming)
- `backend/app/core/config.py` — konfiguracja aplikacji (env vars)
- `pyproject.toml` — Python tooling (ruff, mypy, pyright, semantic-release)
- `docker-compose.yml` — usługi Docker

## Bezpieczeństwo — zawsze

1. **Secrets**: `ggshield secret scan .` przed commitem nowego kodu auth
2. **Dependencies**: `snyk_code_scan` + `trivy_scan_filesystem` + `semgrep scan` przed PR
3. **Docker**: non-root user w Dockerfile (już skonfigurowane)
4. **Env vars**: `.env` w `.gitignore`, wzorzec w `.env.example`

## Troubleshooting

**Testy nie przechodzą?**
- `docker compose logs backend` — sprawdź błędy
- `docker compose exec backend pytest tests/path/test.py::test_name -v --tb=long`
- `ruff check backend/` — lint errors

**Frontend nie kompiluje?**
- `npm run lint` — ESLint errors (flat config z security plugins)
- `npm run build` — build errors

**Docker issues?**
- `docker compose ps` — status kontenerów
- `docker compose logs -f backend` — logi w czasie rzeczywistym
- `docker compose down && docker compose up -d --build` — pełny restart z rebuildem
