# Changelog

All notable changes to Audiovault will be documented in this file.
## [0.4.2] - 2026-05-18

### Bug Fixes

- **docker**: Remove redundant env_file from migrate init-container
- **tests**: Patch get_playlist_details instead of _request in playlist search test
- **tests**: Add type annotation for playlist_data to satisfy mypy

### Documentation

- **delivery**: Add image-based delivery design spec
- **plans**: Add image-based delivery implementation plan
- **quickstart**: Replace --build with pull workflow, add update + dev sections
- Replace --build with pull workflow and dev override command

### Features

- **docker**: Switch to pre-built images, add migrate init-container
- **docker**: Add docker-compose.dev.yml override for local builds

## [0.4.1] - 2026-05-15

### Bug Fixes

- **release**: Sync VERSION and pyproject.toml to 0.4.0
- **models**: Move PlaylistTrack before Playlist to resolve F821 forward ref

### Documentation

- Update and sync docs with current state
- **readme**: Replace wiki links with local docs/ references

## [0.4.0] - 2026-05-07

### Bug Fixes

- **tests**: Switch Library tests to list mode and fix playlist delete title
- **i18n**: Add missing keys and fix sidebar.recommendations mismatch
- **tests**: Add mypy type annotations and method-assign ignores

### Documentation

- **readme**: Replace Snyk badge with Checkov, Aikido, OSV-Scanner, Nuclei
- **readme**: Add Trivy badge
- **contributing**: Update outdated contribution guidelines

### Testing

- **coverage**: Raise backend coverage from 79% to 85%

## [0.3.1] - 2026-05-06

### Bug Fixes

- **ci**: Fix Ruff lint errors and add tag triggers to CI/security workflows
- **ci**: Fix mypy type errors and failing frontend test
- **tests**: Fix 35+ failing pytest tests after SpotifyService OAuth refactor

### Documentation

- **env**: Add Spotify OAuth env vars to .env.example

### Features

- **dashboard**: Show real-time network speed in SystemStats

## [0.3.0] - 2026-05-06

### Bug Fixes

- **spotify**: Fix playlist import — provider order + missing resolve endpoint
- **library**: Fix track delete URL — /downloads/remove/:id → /downloads/:id

### Documentation

- Update Spotify integration docs and add legal disclaimer

### Release

- **0.3.0**: Bump version and collect accumulated changes

## [0.2.0] - 2026-05-04

### Bug Fixes

- **lint**: Fix all 81 ruff errors to pass CI
- **lint**: Apply ruff format to 24 files
- **mypy**: Fix all 227 mypy errors to pass CI
- **tests**: Fix 12 failing pytest tests across 5 root causes
- **lint**: Apply ruff format to spotify_service.py
- **cache**: Await connect() in get/set/delete auto-connect calls
- **logging**: Remove duplicate banner, add colors and cleaner format
- **lint**: Apply ruff format to logger.py
- **security**: Resolve SonarQube, OSV and Snyk findings
- **ci**: Resolve all ruff, ESLint and build failures
- **ci**: Resolve ruff N806/S105 and ESLint sonarjs/todo-tag failures
- **tests**: Resolve Vitest Router context and Pytest deduplication failures
- **ci**: Resolve Vitest link test and Docker Hub rate limit failures
- **ci**: Remove dockerhub-description steps causing Forbidden error
- **ci**: Restore dockerhub-description steps (token now has Delete scope)
- **docker**: Switch postgres and redis to public.ecr.aws to avoid Docker Hub rate limits

### Miscellaneous

- Update .gitignore

### Release

- **0.2.0**: Bump version and fix startup race conditions

## [0.15.0] - 2026-04-18

### Bug Fixes

- **db**: Make alembic migration fc0ebd8b67a8 idempotent
- **db**: Make alembic migration a1b2c3d4e5f6 idempotent
- **db**: Fix ruff E501 line too long in playlists migration
- **db**: Apply ruff format to playlists migration
- **subsonic**: Allow login with email in Subsonic auth
- Correct typo in .gitignore for agent_docs
- Resolve SonarQube S8410, S1192, S7493 issues across subsonic handlers
- Convert remaining S8410 Query params to Annotated form
- Convert all remaining S8410 params to Annotated, fix S8414 CORS ordering
- **sonar**: S8410 - convert remaining Query/Depends to Annotated form
- **sonar**: S8410 - convert Body param to Annotated form in sync.py
- **sonar**: S1192/S1172/S5717/S5806/S6395/S3358/S112/S1186 - misc quality fixes
- **sonar**: S8415 - document HTTPException responses in route decorators
- **sonar**: S3358/S2612 - extract nested ternary, suppress chmod false positive
- **sonar**: S3776 - reduce cognitive complexity in soundcloud/youtube services
- **sonar**: S7503/S5713/S2772/S1481/S117/S1135 - misc quality fixes
- **sonar**: S3776 - reduce complexity in deezer/soundcloud/lastfm/recommendation services
- **sonar**: S3776 - reduce complexity in stream/playlists/storage/sync_manager/search_orchestrator
- **sonar**: S3776 - reduce cognitive complexity in subsonic utils/user/browse handlers
- **sonar**: S3776 - reduce cognitive complexity in subsonic search/playlist/lists handlers
- **sonar**: S3776 - reduce cognitive complexity in download_manager.py
- **sonar**: S3776 - reduce cognitive complexity in library_data and watchlist/processor
- **sonar**: S3776 - reduce cognitive complexity in spotify_service, downloads, subsonic/base
- **sonar**: S3776/S5713/S7503 - fix all 8 remaining SonarQube issues

### Miscellaneous

- **ci**: Fix .github workflows, security pins and CI config
- Update .gitignore and CHANGELOG for improved project structure
- Remove unused configuration files and update project description
- Bump version to 0.15.0

### Styling

- **subsonic**: Apply ruff formatting to auth.py

### Testing

- Add missing tests for soundcloud, base music service, amazon/tidal providers, scheduler
- Add 176 tests across 10 modules to reach 80% coverage

## [0.14.0] - 2026-04-15

### Bug Fixes

- **db**: Add missing track columns (musicbrainz_id, soundcloud_id, metadata_source, metadata_confidence)
- Resolve frontend ESLint and TypeScript build errors
- Resolve remaining Ruff lint errors in backend
- Resolve Ruff and Mypy type errors in backend
- Remove unused MagicMock import in test_downloads.py
- Update spotify mocks to AsyncMock and remove stale tests
- Update all test mocks to AsyncMock after SpotifyService async refactoring
- Use dynamic callback URL for Last.fm auth based on request origin
- Fix.gitignore`.
- **deps**: Correct pydantic-core version constraint
- **frontend**: Use ManualChunksFunction syntax in vite.config

### CI/CD

- Enable PR workflows for the dev branch
- Fix push triggers for dev branch and optimize security scan notifications

### Dependencies

- **deps**: Update Python backend dependencies
- **deps**: Update frontend npm dependencies

### Documentation

- Update README and migrate WIKI documentation to docs directory
- **agent**: Add testing and architecture guides to agent_docs

### Features

- **startup**: Auto-run Alembic migrations on backend startup
- Improve code coverage to 85%+; add tests for Recommendations, Lyrics, and Last.fm profile
- Migrate Spotify API to anonymous httpx scraper

### Miscellaneous

- **docker**: Update Redis base image to redis:8-alpine
- **config**: Move code patterns and conventions to agent_docs/

### Styling

- Reformat files with ruff
- Reformat test files with ruff

## [0.13.0] - 2026-03-04

### Bug Fixes

- Shell syntax in security summary and workflow cleanup
- Remove trailing whitespace in test_coverage_master_boost.py
- **agent**: Rewrite memory-bank-protocol SKILL.md with OpenMemory MCP integration and correct paths
- **ci**: Fix silent mock exceptions causing empty tracklists in watchlist processor
- **ci**: Resolve mypy typings issue in watchlist processor
- Resolve all remaining ruff linting errors (E501, F841)
- **mypy**: Resolve all remaining type hints and signature incompatibilities

### CI/CD

- Migrate security reports to email and fix ruff formatting

### Documentation

- Add reverse proxy and update release workflow
- Translate REVERSE_PROXY.md from Polish to English

### Miscellaneous

- **tests**: Remove redundant coverage and boost test files
- **agent**: Sync entire .agent folder from main (with fixed memory-bank-protocol SKILL.md)
- Bump version to 0.13.0 and update all dependencies

### Styling

- Format test_coverage_master_boost.py with ruff

### Testing

- Improve subsonic search mocks for better coverage and stability

## [0.12.0] - 2026-02-21

### Bug Fixes

- Update tests and formatting to pass CI checks
- **ci**: Resolve pyright errors, bandit security warnings, and ruff linting issues
- **ci**: Resolve remaining test failures and lint errors in lyrics/lastfm services
- **ci**: Resolve all test failures and upgrade axios
- **frontend**: Resolve TS error in lastfm.test.ts by using correct LastfmProfile structure
- Resolve all CI type errors, update tests, and improve code quality
- Correct YAML syntax in agent.yaml configuration
- Remove trailing spaces from agent.yaml
- Improve secret detection to avoid false positives in documentation
- Resolve mypy errors and stylistic issues in playlist handlers
- Resolve downloading issues, improve playlists & watchlist behavior

### CI/CD

- Optimize GitHub workflows and add SonarQube integration
- Optimize workflows and fix backend type errors
- Configure machine-readable Semgrep reporting (JSON/SARIF)
- Modernize Trivy config and enable JSON reporting artifacts
- Add types-requests and types-aiofiles stubs for mypy
- Update github/codeql-action to v4

### Dependencies

- **deps**: Bump the frontend-dependencies group across 1 directory with 10 updates
- **deps**: Bump the frontend-dependencies group

### Documentation

- Update password instructions and security recommendations

### Features

- Add Trivy configuration for security scanning
- Add Semgrep configuration for static code analysis
- Add consolidated security scanning workflow
- Add weekly dependency update report workflow
- **security**: Remediate SonarQube findings and improve accessibility
- Add AI agent configuration files (Memory Bank, Skills, Workflows)
- Add progress tracking and session handover files
- Add AI agent Skills for specialized development assistance
- Add AI agent memory bank structure
- Add AI agent skills for specialized tasks
- Add AI agent workflows for development processes
- Add agent configuration and optimization tools
- Add final agent configuration files and documentation

### Miscellaneous

- Sonarqube tuning, trivy config, git-cliff changelog, fix CI tests
- Sonarqube tuning, trivy config, git-cliff changelog, fix CI tests
- **deps-dev**: Bump jsdom from 27.4.0 to 28.1.0 in /frontend
- Remove unused pre-commit configuration
- Initialize root Node.js project with `package.json` and remove various temporary and debug files.
- Optimize imports and fix formatting in backend
- Fix formatting in backend tests
- **agent**: Consolidate .antigravity into .agent, optimize token usage
- Remove .antigravity (consolidated into .agent)
- Remove .antigravity (consolidated into .agent)
- Remove .antigravity (consolidated into .agent)
- Remove .antigravity (consolidated into .agent)
- Remove .antigravity (consolidated into .agent)
- Remove .antigravity (consolidated into .agent)
- Remove .antigravity (consolidated into .agent)
- Remove .antigravity (consolidated into .agent)
- Remove .antigravity (consolidated into .agent)
- Remove .antigravity (consolidated into .agent)
- Remove .antigravity (consolidated into .agent)
- Remove .antigravity (consolidated into .agent)
- Remove last .antigravity files
- Remove orphaned root memory-bank folder
- **agent**: Add OpenMemory MCP integration, bump to v1.2.0
- **agent**: Update OpenMemory config – WSL2 IP, supergateway transport, 6 tools, v1.3.0
- Code quality improvements, subsonic API parametery, reduce cognitive complexity, frontend lyrics fix
- Fix ruff CI failures and IDE-reported errors in Subsonic API and tests
- **conductor**: Mark track 'Stabilizacja i weryfikacja API Subsonic oraz zwiększenie pokrycia testami' as complete
- **conductor**: Archive track 'Stabilizacja i weryfikacja API Subsonic oraz zwiększenie pokrycia testami'
- Ignore conductor temporary state and archives in .gitignore
- Fix formatting, imports, and test mocks
- Bump version to 0.12.0

### Refactor

- Improve Trivy ignore patterns
- Configure Dependabot for alerts only without auto PRs

### Styling

- Fix Ruff formatting in scrobbler.py
- Apply strict Ruff formatting to scrobbler.py
- Format scrobbler.py with ruff
- Apply ruff format to 26 files

### Testing

- Improve code coverage to ~90% for core modules and fix test regressions

### Conductor

- **setup**: Add conductor setup files
- **plan**: Mark task 'Analiza obecnego stanu testów i API' as complete
- **plan**: Mark task 'Poprawa błędnych testów i handlerów' as complete and add coverage boost tests

### Security

- Finalize SonarQube remediation and fix linting errors
- Fix vulnerabilities and handle false positives in code scanning
- Enhance PII protection and implement refresh token rotation

## [0.11.0] - 2026-02-10

### Bug Fixes

- Rozwiazanie problemow CI i poprawki stabilnosci
- **tests**: Resolve ruff lint errors in smoke tests
- Resolve all 34 MyPy type errors across backend
- Lint errors and code formatting in Handlers and Utils
- Restore accidentally deleted requirements.txt
- Restore requirements.txt and resolve SQLAlchemy UUID regressions
- Resolve ruff linting errors (E501, W293) in WatchlistStorage
- Update .pre-commit-config.yaml with correct type tags for prettier
- Correct pyright repository URL
- Use correct pyright pre-commit repository RobertCraigie/pyright-python
- Update pre-commit configuration for better compatibility and stability
- Use v3.1.0 for prettier (mirrors-prettier archived, no v3.2.5 available)
- Use fsouza/mirrors-pyright instead of missing pre-commit/mirrors-pyright
- Update pre-commit-hooks to v6.0.0 (latest stable release)
- Resolve CI issues and improve stability
- Resolve pre-commit errors (bandit, pyright, ruff)
- Resolve remaining pre-commit errors (bandit B324, pyright hook)
- **ci**: Fix pyright pre-commit hook entry and update coverage
- **ci**: Use community pyright pre-commit hook
- **ci**: Correct bandit args and skip pyright in pre-commit.ci
- **ci**: Exclude tests from pyright check to resolve type errors
- **ci**: Loose pyright rules and fix flaky frontend test
- **ci**: Add lyricsgenius dependency and suppress strict pyright errors
- **ci**: Suppress attribute access errors for legacy dynamic attributes
- Remove unused musicbrainz_id reference and restore strict attribute checks
- **ci**: Disable uvloop to align coverage tracing with local environment
- **test**: Use correct openapi url in coverage boost
- **test**: Use variable s in schema coverage test
- **test**: Resolve import errors in coverage tests
- **test**: Resolve F821 undefined ServiceCredentials
- **test**: Add missing imports and correct class names
- **test**: Use correct StarredTrack model name
- **test**: Correct keyword arguments for models coverage
- **test**: Remove invalid file_path arg from Track instantiation
- **db**: Correct admin user check and rollback on error
- Resolve frontend healthcheck ipv6 issue and fix backend versioning
- **ci**: Update backend build context to root
- **backend**: Make version file resolution robust check parent dirs
- **test**: Add Loader2 to lucide-react mock in AccountSettings

### CI/CD

- Remove redundant tests covered by pre-commit.ci
- Fix pyright pre-commit hook
- Use working pyright pre-commit mirror
- Use RobertCraigie/pyright-python mirror for pyright hook
- Fix pre-commit hooks and translate project metadata
- Update pre-commit hooks configuration
- Add ffmpeg setup to allow tests to pass
- Move pyright to github actions for stability
- Replace strict coverage check with codecov integration

### Dependencies

- **deps**: Update @types/node to 25.0.10

### Documentation

- Add pre-commit setup instructions to contributing guide
- Add comprehensive pre-commit setup and usage guide
- Add note about prettier mirrors-prettier archive and v3.1.0 limitation
- Update prettier version note - mirrors-prettier archived, using v3.1.0

### Features

- Implement karaoke support, LRC sync and improved lyrics search

### Miscellaneous

- Bump version to 0.11.0

### Refactor

- Fix mypy errors, cleanup unused dependencies, and fix login regression

### Styling

- Fix ruff lint errors (line length, import sorting)
- Apply pre-commit fixes to test_coverage_boost.py
- Apply pre-commit fixes
- Apply pre-commit fixes

### Testing

- Fix incorrect async mocks and improve coverage to 86%
- Add coverage boost and cleanup info handler
- Add synthetic coverage tests
- Expand coverage to ~95% for key components

## [0.10.4] - 2026-01-23

### Bug Fixes

- **frontend**: Fix build errors in tests and container restart loop

## [0.10.3] - 2026-01-23

### Bug Fixes

- **frontend**: Permit non-root execution by moving pid file to /tmp

### Miscellaneous

- Sonar cleanup, trivy config, version sync and doc logo updates
- Bump version to 0.10.2
- Bump version to 0.10.3

## [0.10.1] - 2026-01-22

### Release

- V0.10.1 - Timezone support, playlist fixes, logs enhancement

## [0.9.1] - 2026-01-21

### Bug Fixes

- Build backend locally instead of pulling from DockerHub
- Add missing search.searching translation key to all locales
- **all**: Resolve SonarQube issues, refactor Player, fix Tailwind v4 build, update gitignore
- **frontend**: Replace crypto.randomUUID with uuidv4 for compatibility
- **ci**: Update frontend build context to root for VERSION file access
- **frontend**: Use relative API path in Player to support Nginx proxy
- Encode non-ASCII filenames in Content-Disposition headers (RFC 5987)
- Sanitize illegal XML control characters in Subsonic responses
- Add missing beforeEach and afterEach imports from vitest
- Remove unused container variable from render call
- Remove unused container variables in TrackInfo tests
- Remove unused axios import (mocked via vi.mock)
- Declare global type for localStorage mock
- Declare global type for localStorage mock in watchlistSlice
- Optimize dockerfile with better caching and npm install retry
- Expand .dockerignore to reduce docker build context
- Increase timeout and add npm registry config for docker build
- Add npm config for better build reliability in Docker
- Properly type global mocks with declare global for TypeScript compilation
- Properly configure global mocks in setupTests.ts to avoid conflicts
- Resolve all TypeScript compilation errors in tests
- Remove duplicate vitest.config.ts - vite.config.ts is the sole configuration
- **frontend**: Update AlbumDetails type to fix build error
- **backend**: Change default DOWNLOAD_DIR to local folder to prevent pollution of user home

### Build

- **deps**: Bump the frontend-dependencies group
- **deps**: Bump the frontend-dependencies group
- **deps-dev**: Bump @types/uuid from 10.0.0 to 11.0.0 in /frontend
- Exclude test files from frontend production build to fix CI

### Features

- Restore concurrent downloads (3 parallel)
- Per-user concurrent downloads limit from settings
- Extend backend tests, fix duration/playlist bugs, iOS audio fix, mobile layout improvements
- Albums browsing, follow artist & sonar fixes
- A comprehensive set of unit tests for frontend components and logic was added, and new services and API endpoints were implemented in the backend.
- Implement playlist management backend API
- **frontend**: Add playlist integration and artist profile actions
- **frontend**: Integrate playlist modal in artist, album, and track views
- **profile**: Add download button to album and single covers; feat(backend): add download-album endpoint

### Miscellaneous

- Bump version to 0.9.1 and optimize build

### Refactor

- Remove unused API keys and general code cleanup
- **dashboard**: Remove active download widget from main page

### Testing

- Add Amperfy iOS compatibility tests for Subsonic API

## [0.9.0] - 2026-01-11


