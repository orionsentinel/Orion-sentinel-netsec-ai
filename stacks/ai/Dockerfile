FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY pyproject.toml .

# Install package in editable mode
RUN pip install -e .

# Create data directory
RUN mkdir -p /data /config

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "orion_ai.soar.service"]
