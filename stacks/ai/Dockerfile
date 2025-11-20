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
# Dockerfile for Orion Sentinel AI Service
# Optimized for Raspberry Pi 5 (ARM64) with AI Hat

FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ /app/src/
COPY main.py /app/

# Create log directory
RUN mkdir -p /var/log/ai

# Set Python path
ENV PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Default command (can be overridden in docker-compose.yml)
CMD ["python", "main.py", "--mode", "batch"]
