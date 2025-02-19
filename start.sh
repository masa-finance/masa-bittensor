#!/bin/bash
set -e

# Source .env if it exists
[ -f .env ] && source .env

# Basic setup
SUBTENSOR_NETWORK=${SUBTENSOR_NETWORK}
NETUID=${NETUID}

# Set default counts if not provided
VALIDATOR_COUNT=${VALIDATOR_COUNT:-0}
MINER_COUNT=${MINER_COUNT:-1}

echo "Starting nodes for network: $SUBTENSOR_NETWORK (subnet $NETUID)"
echo "Validator count: $VALIDATOR_COUNT"
echo "Miner count: $MINER_COUNT"

# Pull latest image
echo "Pulling latest image..."
docker pull masaengineering/masa-bittensor:latest

# Create .bittensor directory if it doesn't exist
mkdir -p .bittensor
chmod 777 .bittensor

# Base ports - use environment variables with no defaults
BASE_VALIDATOR_AXON_PORT=${VALIDATOR_AXON_PORT}
BASE_VALIDATOR_METRICS_PORT=${VALIDATOR_METRICS_PORT}
BASE_VALIDATOR_GRAFANA_PORT=${VALIDATOR_GRAFANA_PORT}

BASE_MINER_AXON_PORT=${MINER_PORT}
BASE_MINER_METRICS_PORT=${METRICS_PORT}
BASE_MINER_GRAFANA_PORT=${GRAFANA_PORT}

# Function to start a node
start_node() {
    local role=$1
    local instance_num=$2
    local base_axon_port=$3
    local base_metrics_port=$4
    local base_grafana_port=$5

    # Calculate ports for this instance
    local axon_port=$((base_axon_port + instance_num - 1))
    local metrics_port=$((base_metrics_port + instance_num - 1))
    local grafana_port=$((base_grafana_port + instance_num - 1))

    echo "Starting $role $instance_num with ports:"
    echo "  Axon: $axon_port"
    echo "  Metrics: $metrics_port"
    echo "  Grafana: $grafana_port"

    # Set role-specific environment variables
    if [ "$role" = "validator" ]; then
        ENV_VARS="-e VALIDATOR_AXON_PORT=$axon_port -e VALIDATOR_METRICS_PORT=$metrics_port -e VALIDATOR_GRAFANA_PORT=$grafana_port"
    else
        ENV_VARS="-e MINER_AXON_PORT=$axon_port -e MINER_METRICS_PORT=$metrics_port -e MINER_GRAFANA_PORT=$grafana_port"
    fi

    docker run -d \
        --name "masa_${role}_${instance_num}" \
        --env-file .env \
        -e ROLE=$role \
        -e NETUID=$NETUID \
        -e SUBTENSOR_NETWORK=$SUBTENSOR_NETWORK \
        -e REPLICA_NUM=$instance_num \
        -e WALLET_NAME=${WALLET_NAME} \
        -e HOTKEY_NAME=${HOTKEY_NAME} \
        -e MASA_BASE_URL=${MASA_BASE_URL} \
        -e API_URL=${API_URL} \
        $ENV_VARS \
        -v $(pwd)/.env:/app/.env \
        -v $(pwd)/.bittensor:/root/.bittensor \
        -v $(pwd)/startup:/app/startup \
        -v $(pwd)/masa:/app/masa \
        -v $(pwd)/neurons:/app/neurons \
        -p $axon_port:$axon_port \
        -p $metrics_port:$metrics_port \
        -p $grafana_port:$grafana_port \
        masaengineering/masa-bittensor:latest
}

# Clean up any existing containers
echo "Cleaning up existing containers..."
docker ps -a | grep 'masa_' | awk '{print $1}' | xargs -r docker rm -f

# Start validators
for i in $(seq 1 $VALIDATOR_COUNT); do
    start_node "validator" $i $BASE_VALIDATOR_AXON_PORT $BASE_VALIDATOR_METRICS_PORT $BASE_VALIDATOR_GRAFANA_PORT
done

# Start miners
for i in $(seq 1 $MINER_COUNT); do
    start_node "miner" $i $BASE_MINER_AXON_PORT $BASE_MINER_METRICS_PORT $BASE_MINER_GRAFANA_PORT
done

echo "All nodes started. Check logs with:"
echo "docker logs --tail 50 masa_validator_N  # where N is the validator number"
echo "docker logs --tail 50 masa_miner_N      # where N is the miner number" 
