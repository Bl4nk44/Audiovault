# Pinned by digest only (reproducible builds; Sonar docker:S8431 forbids tag+digest).
# Image: python:3.14-slim-trixie (Debian 13: ffmpeg 7.1, aria2 1.37, curl 8.14). HIGH/CRITICAL OS-level
# findings incl. unfixed: 215 vs 286 on bookworm (see AV-72).
# Docker Hub (authenticated in CI) instead of ECR: anonymous public.ecr.aws pulls hit 429 on shared
# runners; digests are identical on both registries. Refresh digest on bump.
FROM docker.io/library/python@sha256:35caba83af2fe6da9a5d922f9b0156f21d1246a48278c58a08bd253303ba42e8

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    aria2 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency lock (PEP 751) + source manifest
COPY pylock.toml backend/requirements.txt ./

# Install Python dependencies from the lock for reproducible builds
RUN pip install --no-cache-dir --only-binary :all: --require-hashes -r pylock.toml

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
