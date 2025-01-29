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

# Install Rust and Python packages
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . $HOME/.cargo/env && \
    pip install --upgrade pip

# Set up workspace
WORKDIR /app
COPY . .

# Install Python packages
RUN pip install masa-ai==0.2.7 && \
    pip install -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/app/subnet-config.json
ENV ROLE=validator

# Use entrypoint.py as the container entry point
ENTRYPOINT ["python", "-u"]
CMD ["entrypoint.py"]