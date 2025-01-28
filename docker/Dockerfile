FROM python:3.12-slim AS base

# Install system dependencies and Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        pkg-config \
        libssl-dev && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . $HOME/.cargo/env && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        bittensor \
        torch \
        python-dotenv \
        loguru \
        scipy \
        numpy \
        requests \
        aiohttp \
        prometheus_client

# Cleanup
RUN apt-get remove -y build-essential && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

FROM python:3.12-slim

# Copy dependencies from base
COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Set up workspace
WORKDIR /app

# Copy the entire project
COPY . .

# Install the local package
RUN pip install -e .

ENTRYPOINT ["python"]
CMD ["-u", "docker/orchestrator.py"] 