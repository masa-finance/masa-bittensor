# Use official Python 3.12 image as base
FROM --platform=linux/amd64 python:3.12-slim

# Set environment variables
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from pyproject.toml
RUN pip install --no-cache-dir \
    "bittensor==8.2.0" \
    "loguru==0.7.2" \
    "python-dotenv==0.21.0" \
    "torch==2.3.0" \
    "scikit-learn==1.5.1" \
    "masa-ai==0.2.5" \
    "pytest==7.2.2" \
    "pytest-asyncio==0.21.0" \
    "requests==2.32.3"

# Set up workspace and environment
WORKDIR /app
ENV CONFIG_PATH=/app/subnet-config.json \
    ROLE=validator \
    NETWORK=test \
    PYTHONPATH=/app

# Use Python for entrypoint
ENTRYPOINT ["python", "-u", "/app/startup/entrypoint.py"]