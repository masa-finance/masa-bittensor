#!/bin/bash

# Clone masa-oracle if it doesn't exist
if [ ! -d "../../masa-oracle" ]; then
    echo "Cloning masa-oracle repository..."
    cd ../.. && git clone https://github.com/masa-finance/masa-oracle.git
    cd masa-oracle
    
    # Get latest release tag
    LATEST_TAG=$(git describe --tags `git rev-list --tags --max-count=1`)
    echo "Checking out latest release: $LATEST_TAG"
    git checkout $LATEST_TAG

    # Copy example env file if .env doesn't exist
    if [ ! -f ".env" ]; then
        cp .env.example .env
        echo "Created .env file from example. Please edit ../../masa-oracle/.env with your settings!"
    fi
fi

# Create necessary directories
mkdir -p .masa-keys
mkdir -p config/prometheus
mkdir -p config/grafana/provisioning
mkdir -p wallet

echo "Setup complete!"
echo "1. Edit ../../masa-oracle/.env with your settings"
echo "2. Run the stack:"
echo "   docker compose up --build              # Run core services"
echo "   docker compose --profile monitoring up --build  # Run with monitoring" 