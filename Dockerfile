# Use official Python 3.8 image as base
FROM --platform=linux/amd64 python:3.8-slim

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

# Install Python dependencies
RUN pip install --no-cache-dir \
    "bittensor>=8.2.0" \
    "bittensor-wallet>=3.0.0" \
    "fiber-py>=0.3.0"

# Set up workspace and environment
WORKDIR /app
ENV CONFIG_PATH=/app/subnet-config.json \
    ROLE=validator \
    NETWORK=test \
    NETUID=165 \
    PYTHONPATH=/app

# Use Python for entrypoint
ENTRYPOINT ["python", "-u", "/app/startup/entrypoint.py"]