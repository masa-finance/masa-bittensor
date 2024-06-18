# Use the official Ubuntu base image
FROM ubuntu:latest

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    clang \
    curl \
    git \
    make \
    libssl-dev \
    protobuf-compiler \
    llvm \
    libudev-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    /bin/bash -c "source $HOME/.cargo/env && \
    rustup default stable && \
    rustup update && \
    rustup target add wasm32-unknown-unknown && \
    rustup toolchain install nightly && \
    rustup target add --toolchain nightly wasm32-unknown-unknown"

# Clone the subtensor repository
RUN git clone https://github.com/opentensor/subtensor.git

# Copy the localnet.sh script into the subtensor/scripts directory
COPY scripts/localnet.sh /subtensor/scripts/localnet.sh

# Set the working directory
WORKDIR /subtensor

# Build the subtensor project
RUN git checkout main && \
    /bin/bash -c "source $HOME/.cargo/env && \
    cargo build --release --features runtime-benchmarks,pow-faucet"

# Make localnet.sh executable
RUN chmod +x /subtensor/scripts/localnet.sh

# Set the entry point to run localnet.sh
ENTRYPOINT ["/subtensor/scripts/localnet.sh"]
