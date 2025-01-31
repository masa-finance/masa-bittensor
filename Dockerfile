# Build stage for Rust components
FROM --platform=$TARGETPLATFORM rust:1.74-bullseye as builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-dev \
        pkg-config \
        libssl-dev \
        libffi-dev \
        libsodium-dev \
        libc6-dev \
        lld \
        clang && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Set up Rust environment
ENV RUSTFLAGS="-C linker=clang -C link-arg=-fuse-ld=lld"
ENV SODIUM_INSTALL=system

# Install maturin for building
RUN pip3 install maturin==1.4.0

# Build bittensor-wallet wheel
RUN pip3 install "bittensor-wallet==2.1.3" --target /wheels

# Final stage
FROM --platform=$TARGETPLATFORM python:3.12-bullseye

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
        libc6-dev \
        cmake \
        automake \
        libtool \
        autoconf \
        lld \
        clang && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Copy wheels from builder
COPY --from=builder /wheels /wheels

# Install base Python setup
RUN pip install --no-cache-dir "setuptools~=70.0.0" wheel

# Install basic utilities and logging
RUN pip install --no-cache-dir \
    "loguru>=0.7.0" \
    "python-dotenv>=0.21.0" \
    "requests>=2.32.0" \
    "munch~=2.5.0" \
    "pyyaml>=6.0.1" \
    "prometheus-client>=0.17.1" \
    "termcolor>=2.4.0" \
    "colorama~=0.4.6" \
    "rich>=13.9.0"

# Install scientific and ML packages
RUN pip install --no-cache-dir \
    "numpy~=2.0.1" \
    "scipy>=1.12.0" \
    "scikit-learn>=1.5.1"

# Install web and async packages
RUN pip install --no-cache-dir \
    "nest-asyncio>=1.5.0" \
    "aiohttp~=3.9" \
    "fastapi~=0.110.1" \
    "uvicorn>=0.25.0" \
    "pydantic>=2.3,<3" \
    "websockets>=14.1"

# Install blockchain and crypto packages
RUN pip install --no-cache-dir \
    "scalecodec==1.2.11" \
    "substrate-interface~=1.7.9" \
    "msgpack-numpy-opentensor~=0.5.0" \
    "netaddr>=1.3.0" \
    "python-statemachine~=2.1" \
    "retry>=0.9.2" \
    "python-Levenshtein>=0.26.1" \
    "cryptography~=43.0.1" \
    "base58>=2.0.1" \
    "eth-utils<2.3.0" \
    "password-strength>=0.0.3.post2"

# Install crypto bindings
RUN pip install --no-cache-dir \
    "py-bip39-bindings==0.1.11" \
    "py-sr25519-bindings<1,>=0.2.0" \
    "py-ed25519-zebra-bindings<2,>=1.0"

# Install ansible packages
RUN pip install --no-cache-dir \
    "ansible>=9.3.0" \
    "ansible-vault>=2.1.0"

# Install bittensor and its dependencies
RUN pip install --no-cache-dir \
    /wheels/bittensor_wallet-2.1.3-*.whl \
    "bittensor==8.2.0" \
    "aiohttp>=3.8.1" \
    "base58>=2.1.1" \
    "cryptography>=41.0.1" \
    "fastapi>=0.110.0" \
    "netaddr>=0.8.0" \
    "numpy>=2.0.0" \
    "pycryptodome>=3.18.0" \
    "pydantic>=2.3.0" \
    "python-dotenv>=0.21.0" \
    "requests>=2.31.0" \
    "scalecodec>=1.2.0" \
    "substrate-interface>=1.7.4" \
    "torch>=2.0.0" \
    "websockets>=12.0"

# Install remaining packages
RUN pip install --no-cache-dir \
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