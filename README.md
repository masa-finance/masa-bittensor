# Docker Setup for Masa Bittensor

This directory contains all Docker-related files for running Masa Bittensor nodes.

## Directory Structure

```
docker/
├── Dockerfile              # Multi-stage build for validator/miner nodes
├── docker-compose.yml      # Compose file for running services
├── .dockerignore          # Files to exclude from builds
├── config/                # Configuration files
│   ├── prometheus/       # Prometheus config
│   └── grafana/         # Grafana config and dashboards
└── subnet-config.json    # Subnet configuration
```

## Prerequisites

- Docker Engine 24.0.0+
- Docker Compose v2.20.0+
- A funded Bittensor wallet (see Wallet Setup below)

## Quick Start

1. Change to the docker directory:
   ```bash
   cd docker
   ```

2. Set up your wallet (see Wallet Setup section)

3. Start the services:
   ```bash
   # Start one validator and one miner
   docker compose up --build validator miner
   
   # Or start multiple instances
   VALIDATOR_COUNT=2 MINER_COUNT=3 docker compose up --build
   ```

## Wallet Setup

You have two options for wallet setup:

1. Using an existing wallet:
   - Your wallet should be in the `.bittensor` directory at the project root
   - This directory is gitignored for security

2. Using a mnemonic:
   - Copy `.env.example` to `.env` in the project root
   - Add your coldkey mnemonic to the `.env` file:
     ```
     COLDKEY_MNEMONIC="your twelve word mnemonic phrase here"
     ```
   - The `.env` file is gitignored for security

## Running Services

From the `docker` directory:

1. Start services with default counts (1 each):
   ```bash
   docker compose up --build
   ```

2. Scale services for multiple subnets:
   ```bash
   # Run 2 validators and 3 miners
   VALIDATOR_COUNT=2 MINER_COUNT=3 docker compose up --build

   # Add more validators to running setup
   docker compose up --scale validator=4 --no-recreate
   ```

## Environment Variables

Network Configuration:
- `NETWORK`: Network to connect to (default: test)
- `NETUID`: Subnet UID (default: 249)
- `CONFIG_PATH`: Path to subnet config (default: subnet-config.json)
- `COLDKEY_MNEMONIC`: Your wallet's coldkey mnemonic

Scaling Configuration:
- `VALIDATOR_COUNT`: Number of validator instances (default: 1)
- `MINER_COUNT`: Number of miner instances (default: 1)

Port Ranges:
- Validators:
  - API ports: 8091-8347 (256 ports)
  - Metrics ports: 9100-9356 (256 ports)
  - Override with `PORT` and `METRICS_PORT`

- Miners:
  - API ports: 8348-8604 (256 ports)
  - Metrics ports: 9357-9613 (256 ports)
  - Override with `PORT` and `METRICS_PORT`

Monitoring Ports:
- Prometheus: 9090
- Grafana: 3000
- Node Exporter: 9100
- Portainer: 9000

## Port Allocation

Each subnet can support up to 256 nodes of each type:

1. Validator Ports:
   - API: 8091 + (instance_number - 1)
   - Metrics: 9100 + (instance_number - 1)

2. Miner Ports:
   - API: 8348 + (instance_number - 1)
   - Metrics: 9357 + (instance_number - 1)

Example:
```bash
# First validator: 8091/9100
# Second validator: 8092/9101
# First miner: 8348/9357
# Second miner: 8349/9358
```

## Monitoring

The setup includes:
- Prometheus (port 9090)
- Grafana (port 3000)
- Node Exporter
- Portainer (port 9000)

Access Grafana at http://localhost:3000 (default credentials: admin/admin)

## Troubleshooting

1. Check service logs:
   ```bash
   # All validators
   docker compose logs validator
   # Specific validator
   docker compose logs validator_1
   
   # All miners
   docker compose logs miner
   # Specific miner
   docker compose logs miner_1
   ```

2. Check metrics:
   - Validators: http://localhost:9100/metrics (9101, 9102, etc.)
   - Miners: http://localhost:9357/metrics (9358, 9359, etc.)

3. Common Issues:
   - Port conflicts: Ensure no other services use the port ranges
   - Container names: Use `docker compose ps` to see actual container names

## Support

For issues and questions:
- GitHub Issues: [masa-finance/masa-bittensor](https://github.com/masa-finance/masa-bittensor/issues)
- Discord: [Masa Finance Discord](https://discord.gg/masafinance) 