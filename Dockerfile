FROM python:3.12-slim

# Install minimal system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
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

# Install minimal Rust toolchain for crypto compilation
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable && \
    . $HOME/.cargo/env && \
    pip install --no-cache-dir --upgrade pip setuptools wheel

# Install core dependencies first
RUN pip install --no-cache-dir \
    "loguru>=0.7.0" \
    "python-dotenv>=0.21.0" \
    "requests>=2.32.0" \
    "munch>=2.5.0" \
    "pyyaml>=6.0.1" \
    "prometheus-client>=0.17.1" \
    "numpy<2.0.0"

# Install PyTorch CPU version
RUN pip install --no-cache-dir torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu

# Install scientific packages with minimal dependencies
RUN pip install --no-cache-dir \
    "scikit-learn>=1.5.0" \
    --only-binary=:all:

# Install minimal bittensor components with pre-built wheels where possible
RUN pip install --no-cache-dir --only-binary=:all: \
        "bittensor-wallet>=2.0.0" \
        "bittensor-cli>=8.4.0" \
        "bt-decode>=0.4.0" \
        "substrate-interface>=1.7.0" \
    && pip install --no-cache-dir \
        "masa-ai>=0.2.5" \
        "pytest>=7.2.0" \
        "pytest-asyncio>=0.21.0"

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