# Changelog

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

