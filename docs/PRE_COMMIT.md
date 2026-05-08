# Pre-Commit Setup & Usage Guide

## What is Pre-Commit?

**pre-commit** runs git hooks automatically before commits to enforce code quality, formatting, and security checks.

## Installation

```bash
pip install pre-commit
```

> **Important**: `pre-commit install` conflicts with ggshield's global git hook (`core.hooksPath` in `~/.gitconfig`). **Do not run `pre-commit install`** — instead run hooks manually or let CI handle it. ggshield secret scanning still runs on every commit via its own global hook.

## Running Hooks

### On modified files

```bash
pre-commit run
```

### On all files

```bash
pre-commit run --all-files
```

### On a specific hook

```bash
pre-commit run ruff --all-files
pre-commit run semgrep --all-files
pre-commit run eslint-frontend --all-files
```

## Configured Hooks

### General checks (`pre-commit-hooks` v5.0.0)

| Hook | Purpose |
|---|---|
| `trailing-whitespace` | Remove trailing whitespace |
| `end-of-file-fixer` | Ensure files end with newline |
| `check-yaml` | Validate YAML syntax |
| `check-json` | Validate JSON syntax |
| `detect-private-key` | Detect private keys in code |
| `check-merge-conflict` | Detect merge conflict markers |

### Ruff (`ruff-pre-commit` v0.15.12)

Runs on `backend/` only.

- `ruff` — lints and auto-fixes Python code (`--fix`)
- `ruff-format` — formats Python code

Configuration in `pyproject.toml`.

### ggshield (v1.50.2)

Secret scanning on staged files. Runs on every commit via pre-commit hook (in addition to the global ggshield git hook if configured).

### Semgrep (v1.75.0)

SAST scan using `.semgrep.yml` from the project root. Excludes `backend/tests/`. Fails on any finding.

```bash
pre-commit run semgrep --all-files
```

### ESLint (local hook)

Runs `npm --prefix frontend run lint` on `frontend/src/` TypeScript/JavaScript files.

Requires `node_modules` to be installed:

```bash
npm --prefix frontend install
```

## Common Scenarios

### First-time setup

```bash
git clone https://github.com/Bl4nk44/Audiovault.git
cd Audiovault
pip install pre-commit
# Don't run pre-commit install — see note above
npm --prefix frontend install
```

### Run all checks before a PR

```bash
pre-commit run --all-files
```

### Fix auto-fixable issues then commit

```bash
pre-commit run ruff --all-files   # auto-fixes Python style
git add -u
git commit -m "fix: apply ruff fixes"
```

## Troubleshooting

### `pre-commit: command not found`

```bash
pip install pre-commit
```

### `ggshield: authentication failed`

```bash
ggshield auth login
```

### ESLint fails with `Cannot find module`

```bash
npm --prefix frontend install
```

### Semgrep slow on first run

Normal — Semgrep downloads rules on first use. Subsequent runs use the cache.

## Updating Hooks

```bash
pre-commit autoupdate
git add .pre-commit-config.yaml
git commit -m "chore: update pre-commit hooks"
```

## Uninstalling

```bash
pre-commit uninstall
pip uninstall pre-commit
```
