# Pre-Commit Setup & Usage Guide

This document provides a comprehensive guide for setting up and using pre-commit hooks in the Audiovault project.

## What is Pre-Commit?

**Pre-commit** is a framework that manages git hooks that run automatically before commits. It ensures code quality, consistency, and security by:

- Automatically formatting code (Ruff, Prettier)
- Running linters (Ruff, Bandit)
- Type checking (Pyright)
- Validating file formats (YAML, TOML)
- Detecting security issues
- Preventing common mistakes

## Installation

### Step 1: Install Pre-Commit Framework

```bash
# Using pip (recommended)
pip install pre-commit

# Using homebrew (macOS)
brew install pre-commit

# Using conda
conda install -c conda-forge pre-commit
```

Verify installation:
```bash
pre-commit --version
```

### Step 2: Install Git Hooks

In your repository root:

```bash
pre-commit install
```

This creates git hooks in `.git/hooks/` that will run pre-commit automatically.

### Step 3: (Optional) Install Pre-Commit Dependencies

Some tools require additional dependencies:

```bash
# Install Python dependencies
pip install -r requirements.txt  # or your requirements file

# Install Node.js dependencies (for Prettier)
cd frontend
npm install
```

## Running Pre-Commit

### Automatic (Default)

Pre-commit runs automatically before each commit:

```bash
git commit -m "feat: Add new feature"
# Pre-commit checks run automatically
```

If any check fails, the commit is blocked. Fix the issues and try again.

### Manual Execution

#### Check Modified Files Only

```bash
pre-commit run
```

#### Check Specific File

```bash
pre-commit run --files backend/app/main.py
```

#### Check All Files

```bash
pre-commit run --all-files
```

#### Run Specific Hook

```bash
pre-commit run ruff --all-files
pre-commit run prettier --all-files
pre-commit run pyright --all-files
```

#### Skip Pre-Commit (Not Recommended)

```bash
git commit --no-verify -m "Your message"
```

## Configured Hooks

### 1. Pre-Commit Hooks (General Checks)

| Hook | Purpose | Files |
| --- | --- | --- |
| `trailing-whitespace` | Remove trailing whitespace | All (except frontend/dist) |
| `end-of-file-fixer` | Ensure files end with newline | All |
| `check-yaml` | Validate YAML syntax | .yaml, .yml |
| `check-toml` | Validate TOML syntax | .toml |
| `check-added-large-files` | Prevent large files (>1MB) | All |
| `check-merge-conflict` | Detect merge conflict markers | All |
| `detect-private-key` | Detect private keys in code | All |
| `mixed-line-ending` | Normalize line endings | All |

### 2. Ruff (Python Formatting & Linting)

**What it does**:
- Fixes code issues automatically (with `--fix` flag)
- Enforces Python style guidelines
- Checks for common errors

**Configuration**: See `pyproject.toml`

```bash
pre-commit run ruff --all-files
```

### 3. Pyright (Python Type Checking)

**What it does**:
- Type checks Python code
- Detects type-related errors
- Improves IDE support

**Configuration**: See `pyproject.toml`

```bash
pre-commit run pyright --all-files
```

**Note**: First run may be slow as it builds its cache.

### 4. Prettier (JavaScript/TypeScript Formatting)

**What it does**:
- Formats JavaScript/TypeScript code consistently
- Formats JSON, YAML, Markdown
- Enforces code style

**Configuration**: See `.prettierrc`

⚠️ **Important Note**: The `pre-commit/mirrors-prettier` repository was **archived on April 11, 2024**. This means:
- ✅ Latest available version: **v3.1.0**
- ❌ No newer versions will be released
- ✅ It still works reliably for current projects
- 📝 Audiovault uses v3.1.0 which is stable and well-tested

If you need newer Prettier features, consider:
1. Using `node-prettier` directly via Node.js (not through pre-commit)
2. Running Prettier as part of your frontend build process
3. Using a Node.js-based pre-commit hook

```bash
pre-commit run prettier --all-files
```

### 5. Bandit (Python Security Scanning)

**What it does**:
- Detects security vulnerabilities in Python
- Checks for insecure patterns
- Flags potential security issues

```bash
pre-commit run bandit --all-files
```

### 6. yamllint (YAML Validation)

**What it does**:
- Validates YAML syntax
- Enforces YAML style guidelines
- Checks formatting

**Configuration**: See `.yamllint`

```bash
pre-commit run yamllint --all-files
```

## Troubleshooting

### Problem: "pre-commit: command not found"

**Solution**:
```bash
pip install pre-commit
pre-commit install
```

If using a virtual environment, ensure it's activated:
```bash
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

### Problem: Pyright Complains About Missing Dependencies

**Symptoms**:
```
Error: Cannot find implementation or library stub for module named "fastapi"
```

**Solution**:
```bash
pip install fastapi sqlalchemy pydantic
pre-commit run pyright --all-files
```

### Problem: Hooks Are Freezing or Very Slow

**Solution**:
```bash
# Clear pre-commit cache
pre-commit clean

# Reinstall hooks
pre-commit install --install-hooks

# Run again
pre-commit run --all-files
```

### Problem: "Prettier: No parser found" Error or "couldn't find remote ref v3.2.5"

**Symptoms**:
```
Error: No parser found for path
fatal: couldn't find remote ref v3.2.5
```

**Explanation**: This happens when trying to use a Prettier version that doesn't exist. The `mirrors-prettier` repo only has releases up to v3.1.0.

**Solution**:
```bash
# Clear and reinstall
pre-commit clean
pre-commit install --install-hooks

# Verify correct version (should be v3.1.0)
cat .pre-commit-config.yaml | grep -A 3 'mirrors-prettier'

# Run again
pre-commit run prettier --all-files
```

### Problem: Hooks Modify Files Unexpectedly

**This is normal!** Some hooks (Ruff, Prettier) are configured to auto-fix issues:

```bash
# Check what changed
git diff

# Stage the fixed files
git add .

# Commit as normal
git commit -m "Your message"
```

### Problem: "fatal: not a git repository"

**Solution**: Make sure you're in the repository root:

```bash
cd /path/to/Audiovault
pre-commit install
```

### Problem: Hook Skips Certain Files

**This is expected.** The configuration excludes:
- `frontend/dist/` - Compiled frontend
- `backend/venv/`, `backend/.venv/` - Virtual environments
- `.lock` files - Lock files
- Binary files (images, audio, fonts)

To check configured exclusions:
```bash
cat .pre-commit-config.yaml
```

## Common Scenarios

### Scenario 1: First-Time Contributor

```bash
# 1. Clone and setup
git clone https://github.com/your-fork/Audiovault.git
cd Audiovault

# 2. Install pre-commit
pip install pre-commit
pre-commit install

# 3. Install project dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 4. Create feature branch
git checkout -b feature/my-feature

# 5. Make changes and commit
# Pre-commit runs automatically!
git commit -m "feat: Add my feature"
```

### Scenario 2: Committing Backend Changes

```bash
# Edit Python files in backend/
vim backend/app/services/spotify.py

# Try to commit
git commit -m "fix: Improve Spotify sync"

# Ruff auto-fixes formatting
# Pyright checks types
# If there are issues, fix them and commit again
```

### Scenario 3: Committing Frontend Changes

```bash
# Edit React/TypeScript files
vim frontend/src/components/Player.tsx

# Try to commit
git commit -m "feat: Improve player UI"

# Prettier auto-formats code
# ESLint checks for issues
# If there are issues, fix them and commit again
```

### Scenario 4: Running Pre-Commit on All Files

Before submitting a PR, check all files:

```bash
pre-commit run --all-files

# If there are issues, fix them:
# Some tools auto-fix, others require manual fixes

# After fixes, run again to verify
pre-commit run --all-files

# Then commit
git add .
git commit -m "chore: Apply pre-commit fixes"
```

## Updating Hooks

### Auto-Update (Pre-Commit CI)

The project uses [pre-commit.ci](https://pre-commit.ci) which automatically:
- Checks for hook updates weekly
- Creates pull requests with updates
- Runs updated hooks on all files

No action needed from contributors.

### Manual Update

```bash
# Update all hooks to latest versions
pre-commit autoupdate

# Run with updated hooks
pre-commit run --all-files

# Commit the changes
git add .pre-commit-config.yaml
git commit -m "chore: Update pre-commit hooks"
```

⚠️ **Note**: Prettier will not update beyond v3.1.0 due to `mirrors-prettier` being archived.

## Uninstalling Pre-Commit

If you need to remove pre-commit:

```bash
pre-commit uninstall
pip uninstall pre-commit
```

Note: This is not recommended as the project relies on pre-commit for code quality.

## Configuration Details

### File: `.pre-commit-config.yaml`

This file defines which hooks run and their configuration:

```yaml
ci:
  autofix_prs: true  # Auto-fix PRs when hooks fail
  autoupdate_schedule: weekly  # Check for updates weekly

exclude: ^(pattern)$  # Skip certain files/directories

repos:  # Define repositories with hooks
  - repo: https://github.com/...
    rev: v1.0.0  # Version
    hooks:
      - id: hook-name
        args: [--arg1, --arg2]  # Arguments
        files: ^pattern$  # File pattern to check
        exclude: ^pattern$  # Files to skip
```

### Python Configuration Files

- **`pyproject.toml`**: Ruff and Pyright configuration, Python version

### Frontend Configuration Files

- **`.prettierrc`**: Prettier formatting rules
- **`.prettierignore`**: Files to skip with Prettier

### YAML Configuration

- **`.yamllint`**: YAML linting rules

## Best Practices

✅ **Do**:
- Keep pre-commit installed and updated
- Commit regularly to catch issues early
- Read pre-commit error messages carefully
- Use `--no-verify` only when absolutely necessary
- Ask for help if hooks are confusing
- Check `.pre-commit-config.yaml` for version information

❌ **Don't**:
- Ignore pre-commit failures
- Use `--no-verify` habitually
- Commit with `--no-verify` without review
- Manually apply fixes that pre-commit should handle
- Update to non-existent hook versions

## Additional Resources

- [Pre-Commit Official Documentation](https://pre-commit.com/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pyright Documentation](https://github.com/microsoft/pyright)
- [Prettier Documentation](https://prettier.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Archived mirrors-prettier Repository](https://github.com/pre-commit/mirrors-prettier) (for reference)

## Questions?

If you have questions about pre-commit setup or usage:

1. Check this guide (you might find your answer!)
2. Search [GitHub Issues](https://github.com/Bl4nk44/Audiovault/issues)
3. Ask in [GitHub Discussions](https://github.com/Bl4nk44/Audiovault/discussions)
4. Open a new [Issue](https://github.com/Bl4nk44/Audiovault/issues/new) if you found a bug

---

Happy coding! 🎵
