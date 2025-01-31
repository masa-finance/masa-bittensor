FROM python:3.12-slim-bullseye

# Install minimal system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        pkg-config \
        libssl-dev && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

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
    pip install --no-cache-dir "setuptools~=70.0.0" wheel

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

# Install bittensor and testing packages
RUN pip install --no-cache-dir \
    "bittensor==8.2.0" \
    "bittensor_wallet==2.1.3" \
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