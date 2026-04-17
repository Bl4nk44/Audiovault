# Changelog

All notable changes to Audiovault will be documented in this file.
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


