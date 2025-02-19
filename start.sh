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
ORACLE_COUNT=${ORACLE_COUNT:-0}
TEE_WORKER_COUNT=${TEE_WORKER_COUNT:-0}

# Image configuration
BITTENSOR_IMAGE=${BITTENSOR_IMAGE:-"masaengineering/masa-bittensor:latest"}
ORACLE_IMAGE=${ORACLE_IMAGE:-"masaengineering/oracle:latest"}
TEE_WORKER_IMAGE=${TEE_WORKER_IMAGE:-"masaengineering/tee-worker:latest"}

echo "Starting nodes for network: $SUBTENSOR_NETWORK (subnet $NETUID)"
echo "Validator count: $VALIDATOR_COUNT"
echo "Miner count: $MINER_COUNT"
echo "Oracle count: $ORACLE_COUNT"
echo "TEE Worker count: $TEE_WORKER_COUNT"
echo "Using Bittensor image: $BITTENSOR_IMAGE"
echo "Using Oracle image: $ORACLE_IMAGE"
echo "Using TEE Worker image: $TEE_WORKER_IMAGE"

# Pull latest images
echo "Pulling latest images..."
docker pull $BITTENSOR_IMAGE
docker pull $ORACLE_IMAGE
[ "$TEE_WORKER_COUNT" -gt 0 ] && docker pull $TEE_WORKER_IMAGE

# Create .bittensor directory if it doesn't exist
mkdir -p .bittensor
chmod 777 .bittensor

# Base ports - use environment variables with defaults
VALIDATOR_PORT=${VALIDATOR_PORT:-8091}
VALIDATOR_METRICS_PORT=${VALIDATOR_METRICS_PORT:-8881}
VALIDATOR_GRAFANA_PORT=${VALIDATOR_GRAFANA_PORT:-3001}

MINER_PORT=${MINER_PORT:-8092}
MINER_METRICS_PORT=${MINER_METRICS_PORT:-8882}
MINER_GRAFANA_PORT=${MINER_GRAFANA_PORT:-3002}

ORACLE_PORT=${ORACLE_PORT:-8093}
ORACLE_METRICS_PORT=${ORACLE_METRICS_PORT:-8883}
ORACLE_GRAFANA_PORT=${ORACLE_GRAFANA_PORT:-3003}

TEE_WORKER_PORT=${TEE_WORKER_PORT:-8094}
TEE_WORKER_METRICS_PORT=${TEE_WORKER_METRICS_PORT:-8884}
TEE_WORKER_GRAFANA_PORT=${TEE_WORKER_GRAFANA_PORT:-3004}

# Function to check if a port is available
check_port() {
    local port=$1
    if command -v nc >/dev/null 2>&1; then
        nc -z localhost $port >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            return 1  # Port is in use
        fi
    else
        # Fallback to using /dev/tcp if nc is not available
        (echo >/dev/tcp/localhost/$port) >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            return 1  # Port is in use
        fi
    fi
    return 0  # Port is available
}

# Function to start a node
start_node() {
    local role=$1
    local instance_num=$2
    local base_port=$3
    local base_metrics_port=$4
    local base_grafana_port=$5

    # Calculate ports for this instance
    local port=$((base_port + instance_num - 1))
    local metrics_port=$((base_metrics_port + instance_num - 1))
    local grafana_port=$((base_grafana_port + instance_num - 1))

    echo "Starting $role $instance_num with ports:"
    echo "  Port: $port"
    echo "  Metrics: $metrics_port"
    echo "  Grafana: $grafana_port"

    # Check if ports are available
    if ! check_port $port || ! check_port $metrics_port || ! check_port $grafana_port; then
        echo "Error: One or more ports are already in use for $role $instance_num"
        exit 1
    fi

    # Set role-specific environment variables and image
    case "$role" in
        "validator")
            ENV_VARS="-e VALIDATOR_PORT=$port -e VALIDATOR_METRICS_PORT=$metrics_port -e VALIDATOR_GRAFANA_PORT=$grafana_port"
            IMAGE=$BITTENSOR_IMAGE
            ;;
        "oracle")
            ENV_VARS="-e ORACLE_PORT=$port -e ORACLE_METRICS_PORT=$metrics_port -e ORACLE_GRAFANA_PORT=$grafana_port"
            IMAGE=$ORACLE_IMAGE
            ;;
        "tee-worker")
            ENV_VARS="-e TEE_WORKER_PORT=$port -e TEE_WORKER_METRICS_PORT=$metrics_port -e TEE_WORKER_GRAFANA_PORT=$grafana_port"
            IMAGE=$TEE_WORKER_IMAGE
            ;;
        *)  # miner
            ENV_VARS="-e MINER_PORT=$port -e MINER_METRICS_PORT=$metrics_port -e MINER_GRAFANA_PORT=$grafana_port"
            IMAGE=$BITTENSOR_IMAGE
            ;;
    esac

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
        -p $port:$port \
        -p $metrics_port:$metrics_port \
        -p $grafana_port:$grafana_port \
        $IMAGE
}

# Clean up any existing containers
echo "Cleaning up existing containers..."
docker ps -a | grep 'masa_' | awk '{print $1}' | xargs -r docker rm -f

# Start validators
for i in $(seq 1 $VALIDATOR_COUNT); do
    start_node "validator" $i $VALIDATOR_PORT $VALIDATOR_METRICS_PORT $VALIDATOR_GRAFANA_PORT
done

# Start miners
for i in $(seq 1 $MINER_COUNT); do
    start_node "miner" $i $MINER_PORT $MINER_METRICS_PORT $MINER_GRAFANA_PORT
done

# Start oracles
for i in $(seq 1 $ORACLE_COUNT); do
    start_node "oracle" $i $ORACLE_PORT $ORACLE_METRICS_PORT $ORACLE_GRAFANA_PORT
done

# Start TEE workers
for i in $(seq 1 $TEE_WORKER_COUNT); do
    start_node "tee-worker" $i $TEE_WORKER_PORT $TEE_WORKER_METRICS_PORT $TEE_WORKER_GRAFANA_PORT
done

echo "All nodes started. Check logs with:"
echo "docker logs --tail 50 masa_validator_N  # where N is the validator number"
echo "docker logs --tail 50 masa_miner_N      # where N is the miner number"
echo "docker logs --tail 50 masa_oracle_N     # where N is the oracle number"
echo "docker logs --tail 50 masa_tee-worker_N # where N is the worker number" 
