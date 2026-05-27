# Security Policy

## Reporting a Vulnerability

The Audiovault team takes security vulnerabilities very seriously. We appreciate your efforts to responsibly disclose your findings and will make every effort to acknowledge your contributions.

### How to Report

**Do not open a public issue for security vulnerabilities.** Instead, please report security vulnerabilities by emailing [bl4nk44@pm.me](mailto:bl4nk44@pm.me) with the following details:

1. **Description**: Brief description of the vulnerability
2. **Affected Component**: Where the vulnerability exists (backend, frontend, dependencies, etc.)
3. **Steps to Reproduce**: Clear steps to reproduce the issue
4. **Potential Impact**: What could an attacker do if exploited?
5. **Proof of Concept**: If available, provide code or screenshots
6. **Suggested Fix**: If you have a suggestion, please include it

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Updates**: Every 7 days during investigation
- **Resolution Target**: Within 30 days for critical vulnerabilities

## Security Considerations

### Sensitive Information

**Never include in issues, PRs, or discussions:**

- API keys or authentication tokens
- Database credentials
- Personal or private user information
- Sensitive server configurations

**If you accidentally expose sensitive information:**

1. Contact us immediately at [bl4nk44@pm.me](mailto:bl4nk44@pm.me)
2. Rotate/revoke any exposed credentials
3. We will help remove the information from the repository history

### Automated Security Tooling

Audiovault runs a layered set of security tools across CI/CD, pre-commit, and dependency monitoring. These tools keep the codebase, dependencies, container images, and secrets continuously scanned.

#### CI/CD — GitHub Actions (`.github/workflows/security.yml`)

Runs on every push/PR to `main` and `dev`, on `v*` tags, and on a weekly schedule (Sundays 02:00 UTC).

| Tool | Type | What it scans |
|------|------|---------------|
| **Trivy** (filesystem) | SCA / vuln scan | Dependency CVEs across the repo (CRITICAL/HIGH/MEDIUM), SARIF + JSON artifacts |
| **Trivy** (Docker image) | Container scan | Backend and frontend images built from their Dockerfiles |
| **Trivy** (secret scanner) | Secret detection | Full git history — **fails the build** if secrets are found |
| **Trivy** (license scanner) | License compliance | Flags HIGH/CRITICAL license risks in dependencies |
| **Semgrep** | SAST | Static analysis via `.semgrep.yml` + `auto` ruleset, SARIF + JSON artifacts |
| **Socket.dev** (`socket ci`) | Supply chain | Malware, typosquatting, and maintenance-risk dependencies (`package-lock.json`, `pyproject.toml`) |

A **Security Summary** job aggregates Trivy, Semgrep, and secret-scan results, emails a report (on scheduled runs or any failure), and fails the pipeline if secrets are detected.

#### Dependency Monitoring

| Tool | Type | Notes |
|------|------|-------|
| **Dependabot** (`.github/dependabot.yml`) | Dependency alerts | Monitors npm, pip, Docker base images, and GitHub Actions weekly. Configured **alerts-only** (`open-pull-requests-limit: 0`) — no automatic PRs; review in Security → Dependabot alerts |
| **Weekly Dependency Report** (`.github/workflows/dependency-report.yml`) | Audit report | Runs `pip-audit` (Python) and `npm audit` (frontend) every Monday, opens a GitHub issue with outdated packages, CVEs, and Docker base-image versions |
| **GitHub Security Advisories** | Advisory tracking | Tracks known vulnerabilities affecting the project |

#### Pre-commit & Local Developer Hooks (`.pre-commit-config.yaml`)

Run locally before code reaches CI:

| Tool | Type | Scope |
|------|------|-------|
| **ggshield** (GitGuardian) | Secret scanning | Runs on `git commit` via a global git hook |
| **Semgrep** | SAST | `.semgrep.yml` ruleset, excludes `backend/tests` |
| **Ruff** | Lint + format | Python (`backend/`) |
| **ESLint** | Lint | TypeScript/React (`frontend/src/`) |
| **detect-private-key** + base hooks | Hygiene | Private-key detection, merge-conflict / YAML / JSON checks, trailing whitespace |

> **Note:** SECURITY.md previously listed Snyk — that tool is **not** used. Vulnerability scanning is handled by Trivy, Socket.dev, Dependabot, and the weekly `pip-audit`/`npm audit` report.

## Security Best Practices for Users

When running Audiovault, please follow these guidelines:

### Environment Variables

- **Never commit `.env` files** to version control
- Use strong, unique passwords for all services
- Rotate credentials regularly
- Use environment-specific values for development vs. production

**Example `.env` Security**:

```bash
# ✅ Good - Strong, random password
ADMIN_PASSWORD=Tr0p!c@lL!m0n_K3y$uP3r#Secure_2024

# ❌ Bad - Weak and exposed
ADMIN_PASSWORD=admin123
```

### API Authentication

- Change default admin credentials on first login
- Use strong passwords (minimum 12 characters, mixed case, numbers, special characters)
- Store API tokens securely
- Rotate tokens periodically
- Use authentication only over HTTPS

### Reverse Proxy Setup

- Always use HTTPS for production deployments
- Configure SSL/TLS certificates (use Let's Encrypt)
- Set secure headers in your reverse proxy:
  ```nginx
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-Frame-Options "SAMEORIGIN" always;
  add_header X-XSS-Protection "1; mode=block" always;
  add_header Referrer-Policy "strict-origin-when-cross-origin" always;
  ```

### Database Security

- Use PostgreSQL instead of SQLite for production
- Set strong database passwords
- Restrict database access to trusted hosts only
- Enable encryption at rest and in transit
- Regular backups with secure storage

### File and Folder Permissions

```bash
# Protect sensitive files
chmod 600 .env
chmod 755 ./music_library

# Ensure only root can read
chown root:root /path/to/config
```

### Docker Security

- **Use official images**: Always pull from official repositories
- **Regular updates**: Keep Docker and base images updated
- **Network isolation**: Use Docker networks instead of exposing ports
- **Resource limits**: Set memory and CPU limits in docker-compose.yml

```yaml
# docker-compose.yml
services:
  backend:
    memory: 2g
    cpus: "1.0"
    restart: unless-stopped
```

### Remote Access Security

When exposing Audiovault to the internet:

- **Use Tailscale or Wireguard** for secure VPN access (preferred)
- **Use fail2ban** to block brute force attempts
- **Enable firewall rules** to restrict access
- **Use DDoS protection** (Cloudflare, etc.)
- **Enable rate limiting** on your reverse proxy

## Security Updates

### Staying Updated

1. **Watch the Repository**

   - Click "Watch" → "Custom" → Select "Releases"
   - You'll be notified of new releases

2. **Subscribe to Announcements**

   - Check the [Discussions](https://github.com/Bl4nk44/Audiovault/discussions) category for security announcements

3. **Regular Docker Image Updates**
   ```bash
   docker compose pull
   docker compose up -d --build
   ```

### Security Patches

Security updates are released as patch versions (e.g., 1.0.1, 1.0.2) and will be applied to:

- `latest` tag
- Specific version tag (e.g., `v1.0.1`)

**Update Immediately**: When a security patch is released, we strongly recommend updating within 48 hours.

## Security in Contributions

If you're contributing code to Audiovault, please:

- ✅ **Do** validate all user input
- ✅ **Do** use parameterized queries to prevent SQL injection
- ✅ **Do** sanitize data before displaying in the UI
- ✅ **Do** follow the OWASP Top 10 guidelines
- ✅ **Do** add security tests for sensitive operations
- ✅ **Do** use HTTP security headers
- ✅ **Do** implement rate limiting where appropriate
- ✅ **Do** document security considerations in your PR

- ❌ **Don't** commit secrets or credentials
- ❌ **Don't** store passwords in plain text
- ❌ **Don't** disable security features
- ❌ **Don't** log sensitive information
- ❌ **Don't** use unsafe deserialization
- ❌ **Don't** trust user input
- ❌ **Don't** expose internal error messages to users

## Compliance & Standards

Audiovault aims to comply with:

- **OWASP Top 10** - Common web application security risks
- **CWE Top 25** - Most dangerous software weaknesses
- **GDPR** - General Data Protection Regulation (for EU users)
- **Best Practices** - Industry-standard security guidelines

## Disclosure Policy

We follow the responsible disclosure principle:

1. **Report** the vulnerability to us privately
2. **Allow time** for us to develop and test a fix (typically 30 days)
3. **Publish** the fix and vulnerability details after resolution
4. **Credit** security researchers in the CHANGELOG (with permission)

## Contact

- **Security Issues**: [bl4nk44@pm.me](mailto:bl4nk44@pm.me)
- **General Questions**: [GitHub Discussions](https://github.com/Bl4nk44/Audiovault/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/Bl4nk44/Audiovault/issues)

## Additional Resources

- [OWASP Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Trivy Documentation](https://trivy.dev/)
- [Semgrep Rules Registry](https://semgrep.dev/explore)
- [Socket.dev](https://socket.dev/)

---

Thank you for helping keep Audiovault secure! 🔐
