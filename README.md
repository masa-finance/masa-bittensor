# Subtensor Network Setup with Docker Compose

This repository contains a Docker Compose setup for running a local Subtensor network with multiple services, including subtensor, subnet, miner, and validator. Each service is defined in its own Dockerfile and script files, which automate the setup and execution of the Subtensor network components.

## Overview

The `docker-compose.yml` file defines four services:

1. **subtensor**: This service sets up the main Subtensor network node and runs the local network script.
2. **subnet**: This service sets up a subnet node that depends on the subtensor node.
3. **miner**: This service sets up a miner node that depends on the subnet node.
4. **validator**: This service sets up a validator node that depends on the subnet node.

Each service has its own Dockerfile and initialization scripts that automate the setup and configuration of the respective nodes.

## File Structure

- `docker-compose.yml`: Docker Compose configuration file defining the services and their dependencies.
- `Dockerfile.subtensor`: Dockerfile for building the subtensor node.
- `Dockerfile.subnet`: Dockerfile for building the subnet node.
- `Dockerfile.miner`: Dockerfile for building the miner node.
- `Dockerfile.validator`: Dockerfile for building the validator node.
- `scripts/`: Directory containing initialization scripts for each service.
  - `localnet.sh`: Script to set up and run the local Subtensor network.
  - `run_faucet.sh`: Script defining the `run_faucet` function used by multiple services.
  - `create_subnet.sh`: Initialization script for the subnet service.
  - `create_miner.sh`: Initialization script for the miner service.
  - `create_validator.sh`: Initialization script for the validator service (same as miner for now).

## Prerequisites

Make sure you have Docker and Docker Compose installed on your system. You can follow the official installation guides:

- [Docker Installation](https://docs.docker.com/get-docker/)
- [Docker Compose Installation](https://docs.docker.com/compose/install/)

## How to Build and Run

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/subtensor-network.git
   cd subtensor-network
   ```

2. **Build the Docker images:**

   ```bash
   docker compose build
   ```

3. **Run the Docker Compose setup:**

   ```bash
   docker compose up
   ```

   This command will start all the defined services and set up the network. The `subtensor` service will initialize first, followed by the `subnet`, `miner`, and `validator` services.

4. **Observe the Interactions:**

   You can observe the logs of the running containers to monitor the interactions between the different services. Open a new terminal and use the following command to view the logs of a specific container:

   ```bash
   docker logs -f <container_name>
   ```

   Replace `<container_name>` with `subtensor_machine`, `subnet_machine`, `miner_machine`, or `validator_machine` to view the logs of the respective service.

## Troubleshooting

If you encounter any issues, you can use the following commands to debug:

- **List running containers:**

  ```bash
  docker ps
  ```

- **Access a running container:**

  ```bash
  docker exec -it <container_name> /bin/bash
  ```

  Replace `<container_name>` with the name of the container you want to access.

- **Stop the Docker Compose setup:**

  ```bash
  docker compose down
  ```

## Notes

- Ensure that the `COLDKEY_PASSWORD` and `HOTKEY_PASSWORD` environment variables are set correctly in the Docker Compose file or in the respective Dockerfiles.
- The `run_faucet` function is defined in the `run_faucet.sh` script, which is sourced in the initialization scripts of the `subnet`, `miner`, and `validator` services.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

Special thanks to the Subtensor team for their work on the Subtensor project. This setup is based on their documentation and codebase.

- [Bittensor GitHub Repository](https://github.com/opentensor/bittensor)
- [Subtensor GitHub Repository](https://github.com/opentensor/subtensor)
- [Bittensor Documentation](https://docs.bittensor.com/)

