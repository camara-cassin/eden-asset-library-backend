# Dockerfile for EDEN Asset Library Backend
FROM python:3.11-slim

ENV POETRY_VERSION=1.8.3 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# Install Python dependencies
COPY pyproject.toml poetry.lock* /app/
RUN poetry install --no-root --no-ansi

# Copy the rest of the application
COPY . /app

# Fly.io expects port 8080 by default
ENV PORT=8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
