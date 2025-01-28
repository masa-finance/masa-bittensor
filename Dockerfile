FROM python:3.12-slim AS builder

# Install system dependencies and Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        pkg-config \
        libssl-dev

# Install Rust and Python packages
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
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

# Final stage
FROM python:3.12-slim

# Copy only the built packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Set up workspace
WORKDIR /app

# Copy the entire project
COPY . .

# Install the local package
RUN pip install -e .

ENTRYPOINT ["python"]
CMD ["-u", "orchestrator.py"] 