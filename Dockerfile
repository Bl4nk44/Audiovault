# Multi-stage build for Audiovault
# Backend structure: backend/requirements.txt
# Frontend structure: frontend/package.json

# Stage 1: Backend builder
FROM python:3.11-slim as backend-builder

WORKDIR /backend

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements from backend folder
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Frontend builder
FROM node:18-alpine as frontend-builder

WORKDIR /frontend

# Copy frontend package files from frontend folder
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source
COPY frontend/ .
RUN npm run build

# Stage 3: Production image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from backend-builder
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy backend source
COPY backend/ .

# Copy frontend built assets
COPY --from=frontend-builder /frontend/dist ./static

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
