# Pinned by digest for reproducible builds; tag kept for readability.
# 3.14-slim-bookworm floating tag carries the latest Debian security patches
# (fixes openssl use-after-free + CPython path-traversal CVEs). Refresh digest on bump.
FROM public.ecr.aws/docker/library/python:3.14-slim-bookworm@sha256:86f975aca15cf04a40b399eebede9aea7c82eae084d1f1a0a6ef6bcaae871a30

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    aria2 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency lock (PEP 751) + source manifest
COPY pylock.toml backend/requirements.txt ./

# Upgrade the bundled pip first (base image ships pip 26.1.2 — CVE-2026-13346,
# arbitrary file install via malicious package indexes), then install from the lock.
RUN pip install --no-cache-dir --upgrade "pip>=26.2.0" && \
    pip install --no-cache-dir --only-binary :all: --require-hashes -r pylock.toml

# Copy application code
COPY backend/ .
COPY VERSION .

# Create non-root user and downloads directory
RUN useradd -m -u 1000 appuser && \
    mkdir -p /downloads /cache && \
    chown -R appuser:appuser /app /downloads /cache && \
    chmod +x /app/entrypoint.sh

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
