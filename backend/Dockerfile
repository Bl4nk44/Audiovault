FROM public.ecr.aws/docker/library/python:3.14.5-slim-bookworm

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
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r pylock.toml

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
