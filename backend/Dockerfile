FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies (ffmpeg is crucial)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Command is overridden in docker-compose, but good to have default
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
