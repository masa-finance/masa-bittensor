FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        netcat-openbsd \
        pkg-config \
        libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Rust and base Python setup with optimized settings
ENV PATH="/root/.cargo/bin:${PATH}"
ENV CARGO_NET_GIT_FETCH_WITH_CLI=true
ENV RUST_BACKTRACE=1
ENV RUSTFLAGS="-C target-cpu=native"
ENV CARGO_PROFILE_RELEASE_LTO=true
ENV CARGO_PROFILE_RELEASE_CODEGEN_UNITS=1

# Install Rust with optimized settings
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . $HOME/.cargo/env && \
    pip install --upgrade pip setuptools wheel

# Install Python packages in stages to better utilize caching
# Stage 1: Install packages without complex build requirements
RUN pip install \
    "loguru==0.7.2" \
    "python-dotenv==0.21.0" \
    "pytest==7.2.2" \
    "pytest-asyncio==0.21.0" \
    "requests==2.32.3"

# Stage 2: Install scientific computing packages
RUN pip install \
    "torch==2.3.0" \
    "scikit-learn==1.5.1" \
    "scipy==1.12.0"

# Stage 3: Install bittensor and related packages with optimized build settings
RUN pip install \
    "masa-ai>=0.2.5" \
    "bittensor>=8.2.0" \
    --no-build-isolation \
    --no-deps \
    --no-cache-dir

# Set up workspace
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/app/subnet-config.json
ENV ROLE=validator
ENV NETWORK=test
ENV NETUID=165

# Copy startup directory
COPY startup /app/startup

# Set Python path
ENV PYTHONPATH=/app

# Use Python script directly as entrypoint
ENTRYPOINT ["python", "-u", "/app/startup/entrypoint.py"]