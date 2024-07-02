# Masa Bittensor Network

This repository contains a Docker Compose setup for running a local Masa Bittensor network with multiple services, including subtensor, subnet, miner, validator, and protocol.

## Prerequisites

- Docker
- Docker Compose
- Make

## Quick Start

1. Clone the repository:
   ```
   git clone https://github.com/masa-finance/masa-bittensor.git
   cd masa-bittensor
   ```

2. Start the network:
   ```
   make up
   ```
   This command will automatically pull the pre-built Docker images from the GitHub Container Registry and start all services.

3. Watch the logs:
   ```
   make logs
   ```
   Monitor the output of all services. It may take about 20 minutes for the validator to have its weights boosted and become fully operational.

## API Testing

Once the network is up and running:

1. Open your browser and navigate to `http://localhost:8000/docs` to see the available API endpoints.

2. Test an endpoint using curl:
   ```
   curl localhost:8000/data/discord/profile/691473028525195315
   ```
   This should return data about the queried Discord profile.

3. In the Docker logs (`make logs`), you should see the validator and miner receiving and processing the request, then sending it to the masa protocol node for actual processing.

## Available Make Commands

- `make up`: Pull images and start all services
- `make down`: Stop and remove all containers
- `make logs`: View logs from all services
- `make pull`: Pull the latest images without starting the services
- `make build`: Build the images locally (not typically needed)

## Troubleshooting

If you encounter issues:

1. Ensure you're using the latest version of Docker and Docker Compose.
2. Try stopping the network (`make down`), pulling the latest images (`make pull`), and starting again (`make up`).
3. Check the logs (`make logs`) for any error messages.

## Contributing

For development workflows and contribution guidelines, please see CONTRIBUTING.md.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
