# Use official bittensor image as base (AMD64 only for now)
FROM --platform=linux/amd64 bittensor/bittensor:latest

# Set environment variables
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install Python 3.12 and create virtualenv
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.12 \
        python3.12-venv \
        python3.12-dev && \
    rm -rf /var/lib/apt/lists/* && \
    python3.12 -m venv /venv && \
    /venv/bin/pip install --upgrade pip

# Install masa-ai in the virtualenv
RUN /venv/bin/pip install "masa-ai==0.2.7"

# Install testing packages in system Python
RUN pip install --no-cache-dir --only-binary :all: \
    "pytest>=7.2.0" \
    "pytest-asyncio>=0.21.0"

# Set up workspace
WORKDIR /app

# Set environment variables
ENV CONFIG_PATH=/app/subnet-config.json \
    ROLE=validator \
    NETWORK=test \
    NETUID=165 \
    PYTHONPATH=/app:/venv/lib/python3.12/site-packages \
    PATH="/venv/bin:$PATH"

# Copy startup directory
COPY startup /app/startup

# Use Python script directly as entrypoint
ENTRYPOINT ["python", "-u", "/app/startup/entrypoint.py"]