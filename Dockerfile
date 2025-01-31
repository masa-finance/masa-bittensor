# Use Python base image
FROM --platform=$TARGETPLATFORM python:3.12-bullseye

# Set environment variables for build optimization
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    SODIUM_INSTALL=system

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

# Install Python packages in optimized layers
# Layer 1: Basic utilities and dependencies
RUN pip install --no-cache-dir --only-binary :all: \
    "setuptools~=70.0.0" \
    wheel \
    "loguru>=0.7.0" \
    "python-dotenv>=0.21.0" \
    "requests>=2.32.0" \
    "munch~=2.5.0" \
    "pyyaml>=6.0.1" \
    "prometheus-client>=0.17.1" \
    "termcolor>=2.4.0" \
    "colorama~=0.4.6" \
    "rich>=13.0.0"

# Layer 2: Scientific and ML packages
RUN pip install --no-cache-dir --only-binary :all: \
    "numpy~=2.0.1" \
    "scipy>=1.12.0" \
    "scikit-learn>=1.5.1"

# Layer 3: Web and async packages
RUN pip install --no-cache-dir --only-binary :all: \
    "nest-asyncio>=1.5.0" \
    "aiohttp~=3.9" \
    "fastapi~=0.110.1" \
    "uvicorn>=0.25.0" \
    "pydantic>=2.3,<3" \
    "websockets>=14.1"

# Layer 4: Blockchain and crypto base packages
RUN pip install --no-cache-dir --only-binary :all: \
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

# Layer 5: Crypto bindings
RUN pip install --no-cache-dir --only-binary :all: \
    "py-bip39-bindings==0.1.11" \
    "py-sr25519-bindings<1,>=0.2.0" \
    "py-ed25519-zebra-bindings<2,>=1.0"

# Layer 6: Ansible packages
RUN pip install --no-cache-dir --only-binary :all: \
    "ansible>=9.3.0" \
    "ansible-vault>=2.1.0"

# Layer 7: Install bittensor dependencies first
RUN pip install --no-cache-dir --only-binary :all: \
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

# Layer 8: Install bittensor and bittensor-wallet (using pre-built wheels)
RUN pip install --no-cache-dir --only-binary :all: \
    "bittensor-commit-reveal==0.2.0" \
    "bittensor==8.2.0" \
    "bittensor-wallet==3.0.0"

# Layer 9: Testing and additional packages
RUN pip install --no-cache-dir --only-binary :all: \
    "masa-ai>=0.2.5" \
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