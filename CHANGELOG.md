# Changelog

## [0.6.5] - 2026-01-03

### Bug Fixes
- Correct nginx.conf path for root build context

## [0.6.4] - 2026-01-03

### Bug Fixes
- Expose VERSION file to frontend build context

## [0.6.3] - 2026-01-03

### Bug Fixes
- Add missing libpq dependencies for postgres driver
- Limit backend dev volumes for production stability

## [0.6.2] - 2026-01-03

### Feature
- Add default admin user creation and implement artist profile page with watchlist functionality.

### Bug Fixes
- backend/requirements.txt to reduce vulnerabilities
- backend/requirements.txt to reduce vulnerabilities

### Refactor
- Optimize Docker images, fix audio playback and security issues

### Chore
- resolve snyk false positives and fix backend test mocks
- update frontend and backend dependencies
- add Snyk configuration to exclude test and build directories.
- restore .env.example with defaults

### Other
- Merge pull request #23 from Bl4nk44/snyk-fix-d1748247f26fc89bd93da324bf7df3ff
- Merge pull request #22 from Bl4nk44/snyk-fix-89da8222b5b34d98b1fd4404ac6253f5

## [0.6.1] - 2025-12-31

### Feature
- Initialize core backend configuration, frontend API client with authentication refresh, and security middleware.

### Bug Fixes
- resolve reverse proxy auth & polish ui

### Chore
- bump the frontend-dependencies group

### Other
- Merge pull request #20 from Bl4nk44/dependabot/npm_and_yarn/frontend/frontend-dependencies-ea98790fba
- Delete .bandit
- Delete GEMINI.md

## [0.6.0] - 2025-12-29

### Bug Fixes
- restrict CORS to local origins
- make all datetime columns timezone aware and update env host
- allow all cors origins for local dev
- use timezone-aware datetime for User.created_at
- update proxy target to localhost for local dev

### Documentation
- add reverse proxy configuration guide

### Other
- Change Audiovault Dashboard image link

## [0.5.12] - 2025-12-23

### Bug Fixes
- resolve eslint issues and activate websocket service

## [0.5.11] - 2025-12-23

### Refactor
- resolve ruff code quality and bandit security issues

## [0.5.10] - 2025-12-22

### Feature
- add cross-platform filename sanitization and units tests

### Bug Fixes
- syntax error in library_maintenance.py
- resolve reliability bug with synchronous file I/O in system logs endpoint
- address remaining IDE warnings (async, exceptions, react keys)
- final lint and build repairs

### Refactor
- resolve SonarQube issues (duplication, accessibility)
- cleanup code smells (datetime, exceptions, imports)
- reduce complexity in downloads.py, stream.py and fix reliability and code smells
- resolve high code smells and reliability issues in downloads, users, spotify and security
- extract logic from App.tsx to reduce cognitive complexity
- huge complexity reduction, extracted services and fixed code smells
- reduce complexity, fix async issues and resolve sonar smells
- reduce cognitive complexity in download_manager and fix frontend warnings

### Chore
- remove test artifacts from tracking and update .gitignore
- exclude translation and json files to avoid false positives
- update docker-compose frontend port mapping and refine README heading styles.
- bump the frontend-dependencies group
- ignore AI_CONTEXT.md file
- remove scanner artifacts from git index

### Other
- Merge pull request #19 from Bl4nk44/dependabot/npm_and_yarn/frontend/frontend-dependencies-5b4f6032b6
- Merge branch 'main' of https://github.com/Bl4nk44/Audiovault
- Update README formatting and section titles

## [0.5.9] - 2025-12-21

- No significant changes documented.

## [0.5.7] - 2025-12-21

### Chore
- update gitignore to exclude sonar-project.properties

