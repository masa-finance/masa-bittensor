# Use official bittensor image as base (AMD64 only for now)
FROM --platform=linux/amd64 bittensor/bittensor:latest

# Set environment variables
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install testing packages
RUN pip install --only-binary :all: \
    "pytest>=7.2.0" \
    "pytest-asyncio>=0.21.0"

# Set up workspace
WORKDIR /app

# Set environment variables
ENV CONFIG_PATH=/app/subnet-config.json \
    ROLE=validator \
    NETWORK=test \
    NETUID=165

# Copy startup directory
COPY startup /app/startup

# Install masa-ai last
RUN pip install "masa-ai==0.2.7"

# Use system Python 3.8 for entrypoint
ENTRYPOINT ["python", "-u", "/app/startup/entrypoint.py"]