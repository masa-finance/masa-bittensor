FROM python:3.12-slim as base

# Install system dependencies and Rust in a single layer, use them, then clean up
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
    pip install --no-cache-dir bittensor torch

# Set working directory
WORKDIR /app

# Copy and install our package
COPY . .
RUN pip install --no-cache-dir -e .

# Cleanup
RUN rustup self uninstall -y && \
    apt-get remove -y build-essential curl && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /root/.cargo /root/.rustup /tmp/* /var/tmp/*

# Now build our application
FROM python:3.12-slim

# Copy only what we need from base
COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=base /app/masa /app/masa
COPY --from=base /app/neurons /app/neurons
COPY --from=base /app/orchestrator.py /app/orchestrator.py

# Build argument to determine node type (validator or miner)
ARG NODE_TYPE=validator

# Add metadata labels
LABEL org.opencontainers.image.title="MASA ${NODE_TYPE}"
LABEL org.opencontainers.image.description="MASA AI ${NODE_TYPE} node for the Bittensor network"
LABEL org.opencontainers.image.source="https://github.com/yourusername/masa-bittensor"

# Set working directory
WORKDIR /app

# Default command to run the orchestrator
ENTRYPOINT ["python"]
CMD ["-u", "orchestrator.py"] 