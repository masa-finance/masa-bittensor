# Use the official Ubuntu base image
FROM ubuntu:latest

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV COLDKEY_PASSWORD=your_coldkey_password
ENV HOTKEY_PASSWORD=your_hotkey_password

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    expect \
    bc \
    && rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment, then install Bittensor
RUN python3 -m venv /opt/bittensor-venv && \
    /opt/bittensor-venv/bin/pip install --upgrade pip && \
    /opt/bittensor-venv/bin/pip install bittensor==7.2.0 && \
    /opt/bittensor-venv/bin/pip install bittensor[torch]

# Copy the subnet creation script
COPY ../functions.sh /app/functions.sh
COPY ./entrypoint.sh /app/entrypoint.sh

# Make the script executable
RUN chmod +x /app/entrypoint.sh

# Set the entry point to run the script
ENTRYPOINT ["/app/entrypoint.sh"]

# Set the PATH to include the virtual environment
ENV PATH="/opt/bittensor-venv/bin:$PATH"

