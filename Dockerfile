# Use official bittensor image as base
FROM bittensor/bittensor:latest

# Set environment variables
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install masa-ai and testing packages
RUN pip install --no-cache-dir "masa-ai==0.2.7" && \
    pip install --no-cache-dir --only-binary :all: \
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