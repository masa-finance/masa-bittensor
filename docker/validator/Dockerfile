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
    /opt/bittensor-venv/bin/pip install bittensor[torch] && \
    /opt/bittensor-venv/bin/pip install python-dotenv

# Copy the validator creation script
COPY scripts/functions.sh /usr/local/bin/functions.sh
COPY scripts/create_validator.sh /usr/local/bin/create_validator.sh

# Copy the neurons and masa directories
COPY neurons /app/neurons
COPY masa /app/masa
COPY requirements.txt /app/requirements.txt
RUN /opt/bittensor-venv/bin/pip install -r /app/requirements.txt

# Set the working directory
WORKDIR /app

# Set the PATH to include the virtual environment
ENV PYTHONPATH="/opt/bittensor-venv/bin:/app:$PYTHONPATH"
ENV PATH="/opt/bittensor-venv/bin:$PATH"

# Make the script executable
RUN chmod +x /usr/local/bin/create_validator.sh

# Set the entry point to run the script
ENTRYPOINT ["/usr/local/bin/create_validator.sh"]

# Add a command to keep the container running
CMD ["tail", "-f", "/dev/null"]
