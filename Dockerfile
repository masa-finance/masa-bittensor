# Use Python 3.12 base image
FROM --platform=linux/amd64 python:3.12-slim-bullseye

# Set environment variables
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        pkg-config \
        libssl-dev \
        libffi-dev \
        libsodium-dev \
        libc6-dev && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        "bittensor>=8.2.0" \
        "bittensor-wallet>=3.0.0" \
        "masa-ai==0.2.7" \
        "pytest>=7.2.0" \
        "pytest-asyncio>=0.21.0"

# Set up workspace
WORKDIR /app

# Set environment variables
ENV CONFIG_PATH=/app/subnet-config.json \
    ROLE=validator \
    NETWORK=test \
    NETUID=165 \
    PYTHONPATH=/app

# Copy startup directory
COPY startup /app/startup

# Use Python script directly as entrypoint
ENTRYPOINT ["python", "-u", "/app/startup/entrypoint.py"]