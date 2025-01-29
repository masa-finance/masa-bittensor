FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        pkg-config \
        libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Rust and base Python setup
ENV PATH="/root/.cargo/bin:${PATH}"
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . $HOME/.cargo/env && \
    pip install --upgrade pip

# Install all dependencies from pyproject.toml
RUN pip install \
    "bittensor>=8.2.0" \
    "loguru==0.7.2" \
    "python-dotenv==0.21.0" \
    "torch==2.3.0" \
    "scikit-learn==1.5.1" \
    "masa-ai>=0.2.5" \
    "pytest==7.2.2" \
    "pytest-asyncio==0.21.0" \
    "requests==2.32.3"

# Set up workspace for our application
WORKDIR /app
COPY . .

# Install our package
RUN pip install -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/app/subnet-config.json
ENV ROLE=validator

# Use startup/entrypoint.py as the container entry point
ENTRYPOINT ["python", "-u"]
CMD ["startup/entrypoint.py"]