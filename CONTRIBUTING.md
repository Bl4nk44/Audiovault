# Contributing to Audiovault

First off, thank you for considering contributing to Audiovault! It's people like you that make Audiovault such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [bl4nk44@pm.me](mailto:bl4nk44@pm.me).

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the [issue list](https://github.com/Bl4nk44/Audiovault/issues) as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps which reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed after following the steps**
- **Explain which behavior you expected to see instead and why**
- **Include screenshots and animated GIFs if possible**
- **Include your environment details** (OS, version, Docker/bare metal setup)
- **Include logs** from `docker compose logs backend` or browser console

Please use the [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md) when creating bug reports.

### Suggesting Enhancements

Enhancement suggestions are tracked as [GitHub Issues](https://github.com/Bl4nk44/Audiovault/issues). When creating an enhancement suggestion, please include:

- **A clear and descriptive title**
- **A step-by-step description of the suggested enhancement**
- **Specific examples to demonstrate the steps**
- **A description of the current behavior and expected behavior**
- **Possible implementation details (optional)**
- **Screenshots and animated GIFs (optional)**

Please use the [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.md) when creating enhancement suggestions.

### Discussions

For questions, ideas, or general discussions that don't fit into bug reports or feature requests, please use [GitHub Discussions](https://github.com/Bl4nk44/Audiovault/discussions). This is a great way to:

- Ask questions about how to use Audiovault
- Share ideas and get feedback
- Discuss potential features before opening an issue

## Development Setup

### Prerequisites

- **Git** - For version control
- **Python 3.10+** - Backend development
- **Node.js 18+** - Frontend development
- **Docker & Docker Compose** - For local development environment
- **PostgreSQL** (optional) - For testing with real database

### Setting Up Your Development Environment

1. **Fork the repository**

   ```bash
   # Navigate to https://github.com/Bl4nk44/Audiovault and click Fork
   ```

2. **Clone your fork**

   ```bash
   git clone https://github.com/your-username/Audiovault.git
   cd Audiovault
   ```

3. **Add upstream remote**

   ```bash
   git remote add upstream https://github.com/Bl4nk44/Audiovault.git
   ```

4. **Create a development branch**

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix-name
   ```

5. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your development settings
   ```

6. **Install pre-commit hooks** (IMPORTANT)

   ```bash
   # Install pre-commit framework
   pip install pre-commit

   # Install git hooks for the repository
   pre-commit install

   # (Optional) Run against all files to check for issues
   pre-commit run --all-files
   ```

   > **What is pre-commit?** Pre-commit automatically runs linters, formatters, and security checks before each commit. This ensures code quality and consistency. Learn more at [pre-commit.com](https://pre-commit.com/)

7. **Start the development environment with Docker**

   ```bash
   docker compose up -d --build
   ```

8. **Check the logs to ensure everything started correctly**
   ```bash
   docker compose logs -f backend
   docker compose logs -f frontend
   ```

### Pre-Commit Configuration

This project uses **pre-commit hooks** to automatically check and fix code quality issues. The configuration includes:

#### What Gets Checked

| Tool | Purpose | Files |
| --- | --- | --- |
| **pre-commit-hooks** | General file checks, trailing whitespace, YAML validation | All |
| **Ruff** | Python linting and formatting | Backend (*.py) |
| **Pyright** | Python type checking | Backend (*.py) |
| **Prettier** | JavaScript/TypeScript formatting | Frontend (*.jsx, *.tsx, *.json, *.yaml, *.md) |
| **Bandit** | Python security scanning | Backend (*.py) |
| **yamllint** | YAML validation | GitHub Actions, docker-compose.yml |

#### Running Pre-Commit Manually

```bash
# Check all files
pre-commit run --all-files

# Check only changed files
pre-commit run

# Skip pre-commit checks (not recommended)
git commit --no-verify

# Update all hooks to latest versions
pre-commit autoupdate
```

#### Troubleshooting Pre-Commit

**Issue**: `pre-commit: command not found`
```bash
# Solution: Install pre-commit
pip install pre-commit
pre-commit install
```

**Issue**: Pyright complains about missing dependencies
```bash
# Solution: Run pre-commit with dependencies
pre-commit run pyright --all-files
```

**Issue**: Prettier or Ruff is slow or freezing
```bash
# Solution: Clear pre-commit cache
pre-commit clean
pre-commit run --all-files
```

**Issue**: Some hooks fail unexpectedly
```bash
# Solution: Reinstall all hooks
pre-commit clean
pre-commit install --install-hooks
pre-commit run --all-files
```

### Backend Development

**Location**: `./backend`

**Tech Stack**: Python, FastAPI, SQLAlchemy

```bash
# Install dependencies (if developing locally without Docker)
cd backend
pip install -r requirements.txt

# Run tests
pytest

# Format code (pre-commit does this automatically)
black .
flake8 .
isort .

# View API documentation
# Open http://localhost:8000/docs in your browser
```

**Key Files**:

- `backend/app/main.py` - FastAPI application entry point
- `backend/app/api/` - API route definitions
- `backend/app/models/` - Database models
- `backend/app/services/` - Business logic
- `backend/app/schemas/` - Pydantic schemas for request/response validation

### Frontend Development

**Location**: `./frontend`

**Tech Stack**: React, TypeScript, TailwindCSS, Framer Motion

```bash
# Install dependencies (if developing locally without Docker)
cd frontend
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Format code (pre-commit does this automatically)
npm run format

# Lint code
npm run lint
```

**Key Directories**:

- `frontend/src/components/` - React components
- `frontend/src/pages/` - Page components
- `frontend/src/hooks/` - Custom React hooks
- `frontend/src/services/` - API client and services
- `frontend/src/types/` - TypeScript type definitions
- `frontend/src/styles/` - TailwindCSS configuration and global styles

## Git Workflow

### Branch Naming Convention

Please use descriptive branch names:

```
feature/add-spotify-sync         # New feature
fix/auth-token-refresh           # Bug fix
docs/update-readme               # Documentation
refactor/simplify-api-calls      # Refactoring
test/add-unit-tests              # Testing
chore/update-dependencies        # Maintenance
```

### Commit Messages

Write clear and descriptive commit messages:

```
# Good ✅
feat: Add Spotify playlist import functionality
fix: Resolve JWT token expiration handling
docs: Update installation guide for macOS
refactor: Simplify music metadata extraction logic

# Avoid ❌
update stuff
fixes
wip
test123
```

**Format**: `<type>: <description>`

**Types**:

- `feat:` - A new feature
- `fix:` - A bug fix
- `docs:` - Documentation only changes
- `refactor:` - Code change that neither fixes a bug nor adds a feature
- `perf:` - Code change that improves performance
- `test:` - Adding or updating tests
- `chore:` - Changes to build process, dependencies, etc.
- `ci:` - Changes to CI configuration
- `style:` - Changes that do not affect code meaning (formatting, missing semicolons, etc.)

### Pull Request Process

1. **Update your branch**

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push to your fork**

   ```bash
   git push origin your-branch-name
   ```

3. **Create a Pull Request**

   - Go to the [Pull Requests](https://github.com/Bl4nk44/Audiovault/pulls) page
   - Click "New Pull Request"
   - Select your branch and provide a clear description
   - Fill out the PR template completely
   - Link any related issues using `Closes #issue-number`

4. **Respond to feedback**

   - Address any review comments
   - Push changes to the same branch (they'll automatically update the PR)
   - Request re-review when ready

5. **Squash commits (if requested)**
   ```bash
   git rebase -i upstream/main
   # Mark commits as 'squash' or 's' to combine them
   git push --force-with-lease origin your-branch-name
   ```

## Code Style Guidelines

### Python (Backend)

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints for function arguments and return values
- Maximum line length: 120 characters (configured in pyproject.toml)
- Use docstrings for all public functions and classes
- Format with `black` and lint with `ruff` and `isort` (pre-commit does this automatically)

**Example**:

```python
def get_user_by_id(user_id: int) -> Optional[User]:
    """Retrieve a user by their ID.

    Args:
        user_id: The unique identifier of the user

    Returns:
        User object if found, None otherwise
    """
    return db.query(User).filter(User.id == user_id).first()
```

### TypeScript/React (Frontend)

- Use TypeScript for all components
- Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use functional components with hooks
- Use meaningful variable and function names
- Format with Prettier (pre-commit does this automatically)
- Lint with ESLint

**Example**:

```typescript
interface PlaylistProps {
  playlistId: string;
  onSelect: (id: string) => void;
}

const PlaylistCard: React.FC<PlaylistProps> = ({ playlistId, onSelect }) => {
  return (
    <div onClick={() => onSelect(playlistId)}>
      {/* Component content */}
    </div>
  );
};
```

## Testing

### Backend Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_spotify_service.py

# Run with verbose output
pytest -v
```

### Frontend Testing

```bash
# Run all tests
npm test

# Run in watch mode
npm test -- --watch

# Generate coverage report
npm test -- --coverage
```

**Please ensure**:

- All tests pass before submitting a PR
- Add tests for new features
- Update tests when modifying existing functionality
- Aim for >80% code coverage for new code

## Documentation

When contributing:

- Update the README.md if adding new features or changing installation steps
- Update the CHANGELOG.md with your changes
- Add docstrings to new functions and classes
- Update Wiki documentation if implementing significant changes
- Add comments for complex logic

## Security

If you discover a security vulnerability, please email [bl4nk44@pm.me](mailto:bl4nk44@pm.me) instead of using the issue tracker. See [SECURITY.md](SECURITY.md) for more details.

## Additional Resources

- [GitHub Documentation](https://docs.github.com)
- [Git Documentation](https://git-scm.com/doc)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [TailwindCSS Documentation](https://tailwindcss.com/docs)
- [Pre-commit Framework](https://pre-commit.com/)

## Questions?

- Check the [Wiki](https://github.com/Bl4nk44/Audiovault/wiki)
- Browse [Discussions](https://github.com/Bl4nk44/Audiovault/discussions)
- Open an [Issue](https://github.com/Bl4nk44/Audiovault/issues)

---

Thank you for contributing to Audiovault! 🎵
