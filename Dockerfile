# Use Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
# PYTHONWARNINGS=ignore::SyntaxWarning suppresses pydub invalid escape sequence warnings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONWARNINGS=ignore::SyntaxWarning

# Install system dependencies:
# - ffmpeg: Required for pydub audio conversion (OGG to WAV)
# - libsndfile1: Required for audio file handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .python-version README.md ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --no-dev

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Run the bot
CMD ["uv", "run", "bot"]
