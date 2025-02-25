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
ENABLE_BOOTNODE=${ENABLE_BOOTNODE:-false}
ORACLE_WORKER_COUNT=${ORACLE_WORKER_COUNT:-0}
TEE_WORKER_COUNT=${TEE_WORKER_COUNT:-0}

# Image configuration
BITTENSOR_IMAGE=${BITTENSOR_IMAGE:-"masaengineering/masa-bittensor:latest"}
ORACLE_IMAGE=${ORACLE_IMAGE:-"masaengineering/oracle:latest"}
TEE_WORKER_IMAGE=${TEE_WORKER_IMAGE:-"masaengineering/tee-worker:latest"}

# Get the host IP address
HOST_IP=$(hostname -I | awk '{print $1}')
echo "Host IP address: $HOST_IP"

echo "Starting nodes for network: $SUBTENSOR_NETWORK (subnet $NETUID)"
echo "Validator count: $VALIDATOR_COUNT"
echo "Miner count: $MINER_COUNT"
echo "Enable bootnode: $ENABLE_BOOTNODE"
echo "Oracle worker count: $ORACLE_WORKER_COUNT"
echo "TEE Worker count: $TEE_WORKER_COUNT"
echo "Using Bittensor image: $BITTENSOR_IMAGE"
echo "Using Oracle image: $ORACLE_IMAGE"
echo "Using TEE Worker image: $TEE_WORKER_IMAGE"

# Pull latest images
echo "Pulling latest images..."
docker pull $BITTENSOR_IMAGE
if [ "$ENABLE_BOOTNODE" = "true" ] || [ "$ORACLE_WORKER_COUNT" -gt 0 ]; then
    docker pull $ORACLE_IMAGE
fi
[ "$TEE_WORKER_COUNT" -gt 0 ] && docker pull $TEE_WORKER_IMAGE

# Create necessary directories if they don't exist
mkdir -p .bittensor
chmod 777 .bittensor

if [ "$ENABLE_BOOTNODE" = "true" ] || [ "$ORACLE_WORKER_COUNT" -gt 0 ]; then
    mkdir -p .masa-bootnode
    chmod 777 .masa-bootnode
    
    if [ "$ORACLE_WORKER_COUNT" -gt 0 ]; then
        mkdir -p .masa-worker
        chmod 777 .masa-worker
    fi
fi

# Base ports - use environment variables with defaults
VALIDATOR_PORT=${VALIDATOR_PORT:-8091}
VALIDATOR_METRICS_PORT=${VALIDATOR_METRICS_PORT:-8881}
VALIDATOR_GRAFANA_PORT=${VALIDATOR_GRAFANA_PORT:-3001}

MINER_PORT=${MINER_PORT:-8092}
MINER_METRICS_PORT=${MINER_METRICS_PORT:-8882}
MINER_GRAFANA_PORT=${MINER_GRAFANA_PORT:-3002}

BOOTNODE_PORT=${BOOTNODE_PORT:-18201}
BOOTNODE_METRICS_PORT=${BOOTNODE_METRICS_PORT:-8893}
BOOTNODE_GRAFANA_PORT=${BOOTNODE_GRAFANA_PORT:-3103}

ORACLE_WORKER_PORT=${ORACLE_WORKER_PORT:-18202}
ORACLE_WORKER_METRICS_PORT=${ORACLE_WORKER_METRICS_PORT:-8894}
ORACLE_WORKER_GRAFANA_PORT=${ORACLE_WORKER_GRAFANA_PORT:-3104}

TEE_WORKER_PORT=${TEE_WORKER_PORT:-8095}
TEE_WORKER_METRICS_PORT=${TEE_WORKER_METRICS_PORT:-8885}
TEE_WORKER_GRAFANA_PORT=${TEE_WORKER_GRAFANA_PORT:-3005}

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

# Function to start a bittensor node (validator or miner)
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

    # Generate wallet and hotkey names for this instance
    local wallet_name="subnet_${NETUID}"
    local hotkey_name="${role}_${instance_num}"
    
    echo "Starting $role $instance_num with ports:"
    echo "  Port: $port"
    echo "  Metrics: $metrics_port"
    echo "  Grafana: $grafana_port"
    echo "  Using wallet: $wallet_name"
    echo "  Using hotkey: $hotkey_name"

    # Check if ports are available
    if ! check_port $port || ! check_port $metrics_port || ! check_port $grafana_port; then
        echo "Error: One or more ports are already in use for $role $instance_num"
        exit 1
    fi

    # Set role-specific environment variables and image
    case "$role" in
        "validator")
            ENV_VARS="-e VALIDATOR_PORT=$port -e VALIDATOR_METRICS_PORT=$metrics_port -e VALIDATOR_GRAFANA_PORT=$grafana_port -e VALIDATOR_AXON_PORT=$port"
            IMAGE=$BITTENSOR_IMAGE
            ;;
        "tee-worker")
            ENV_VARS="-e TEE_WORKER_PORT=$port -e TEE_WORKER_METRICS_PORT=$metrics_port -e TEE_WORKER_GRAFANA_PORT=$grafana_port"
            IMAGE=$TEE_WORKER_IMAGE
            ;;
        *)  # miner
            ENV_VARS="-e MINER_PORT=$port -e MINER_METRICS_PORT=$metrics_port -e MINER_GRAFANA_PORT=$grafana_port -e MINER_AXON_PORT=$port"
            IMAGE=$BITTENSOR_IMAGE
            ;;
    esac

    # Launch bittensor nodes with host networking
    docker run -d \
        --name "masa_${role}_${instance_num}" \
        --network host \
        --env-file .env \
        -e ROLE=$role \
        -e NETUID=$NETUID \
        -e SUBTENSOR_NETWORK=$SUBTENSOR_NETWORK \
        -e REPLICA_NUM=$instance_num \
        -e WALLET_NAME=$wallet_name \
        -e HOTKEY_NAME=$hotkey_name \
        -e MASA_BASE_URL=${MASA_BASE_URL} \
        -e API_URL=${API_URL} \
        -e COLDKEY_MNEMONIC="$COLDKEY_MNEMONIC" \
        -e HOST_IP="$HOST_IP" \
        $ENV_VARS \
        -v $(pwd)/.env:/app/.env \
        -v $(pwd)/.bittensor:/root/.bittensor \
        -v $(pwd)/startup:/app/startup \
        -v $(pwd)/masa:/app/masa \
        -v $(pwd)/neurons:/app/neurons \
        -v $(pwd)/config.json:/app/config.json \
        $IMAGE python -m startup
}

# Function to start a bootnode
start_bootnode() {
    local port=$BOOTNODE_PORT
    local metrics_port=$BOOTNODE_METRICS_PORT
    local grafana_port=$BOOTNODE_GRAFANA_PORT
    
    echo "Starting bootnode with ports:"
    echo "  Port: $port"
    echo "  Metrics: $metrics_port"
    echo "  Grafana: $grafana_port"

    # Check if ports are available
    if ! check_port $port || ! check_port $metrics_port || ! check_port $grafana_port || ! check_port 4001; then
        echo "Error: One or more ports are already in use for bootnode"
        exit 1
    fi

    # Launch bootnode with host networking
    docker run -d \
        --name "masa_bootnode" \
        --hostname "masa_bootnode" \
        --network host \
        -v $(pwd)/bootnode.env:/home/masa/.env \
        -v $(pwd)/.masa-bootnode:/home/masa/.masa \
        $ORACLE_IMAGE \
        --masaDir=/home/masa/.masa \
        --env=hometest \
        --api-enabled \
        --logLevel=debug \
        --port=$port
}

# Function to get the bootnode address
get_bootnode_address() {
    echo "Waiting 15 seconds for bootnode to start..."
    sleep 15
    
    # IMPORTANT: Display full logs to terminal FIRST
    echo "==== FULL BOOTNODE LOGS ===="
    docker logs masa_bootnode
    echo "==== END BOOTNODE LOGS ===="
    
    # Get the complete multiaddress directly
    BOOTNODE_ADDRESS=$(docker logs masa_bootnode 2>&1 | grep -o "/ip4/[^ ]*" | head -1)
    
    if [ -n "$BOOTNODE_ADDRESS" ]; then
        echo "Found complete multiaddress: $BOOTNODE_ADDRESS"
        return 0
    fi
    
    echo "Failed to extract bootnode multiaddress from logs."
    return 1
}

# Function to start an oracle worker
start_oracle_worker() {
    local instance_num=$1
    local bootnodes=$2
    local base_port=$ORACLE_WORKER_PORT
    local base_metrics_port=$ORACLE_WORKER_METRICS_PORT
    local base_grafana_port=$ORACLE_WORKER_GRAFANA_PORT

    # Calculate ports for this instance
    local port=$((base_port + instance_num - 1))
    local metrics_port=$((base_metrics_port + instance_num - 1))
    local grafana_port=$((base_grafana_port + instance_num - 1))
    
    echo "Starting oracle worker $instance_num with ports:"
    echo "  Port: $port"
    echo "  Metrics: $metrics_port"
    echo "  Grafana: $grafana_port"
    
    # Validate bootnode address
    if [[ "$bootnodes" != /* ]]; then
        echo "WARNING: Invalid bootnode address format: $bootnodes"
        echo "Using default bootnode address format with host IP"
        bootnodes="/ip4/$HOST_IP/udp/4001/quic-v1"
    fi
    
    echo "  Using bootnode: $bootnodes"

    # Check if ports are available
    if ! check_port $port || ! check_port $metrics_port || ! check_port $grafana_port; then
        echo "Error: One or more ports are already in use for oracle worker $instance_num"
        exit 1
    fi

    # Launch oracle worker with host networking and IP-based bootnode address
    docker run -d \
        --name "masa_oracle_worker_${instance_num}" \
        --network host \
        --env-file worker.env \
        -v $(pwd)/.masa-worker:/home/masa/.masa \
        $ORACLE_IMAGE \
        --masaDir=/home/masa/.masa \
        --env=hometest \
        --api-enabled \
        --logLevel=debug \
        --port=$port \
        --bootnodes=$bootnodes
}

# Function to display node info
display_node_info() {
    echo -e "\n============= Node Information =============\n"
    
    # Display miner info if any running
    if [ "$MINER_COUNT" -gt 0 ]; then
        echo -e "===== MINER NODES =====\n"
        for i in $(seq 1 $MINER_COUNT); do
            echo "Miner $i:"
            docker logs masa_miner_$i 2>&1 | grep -i "hotkey" | tail -1 || echo "No hotkey info found"
        done
        echo ""
    fi
    
    # Display bootnode info if running
    if [ "$ENABLE_BOOTNODE" = "true" ]; then
        echo -e "===== BOOTNODE =====\n"
        
        # Just show that it's running
        if docker ps -q -f name=masa_bootnode >/dev/null 2>&1; then
            echo "Bootnode: Running"
        else
            echo "Bootnode: Not running or failed to start"
        fi
        echo ""
    fi
    
    # Display oracle worker info if any running
    if [ "$ORACLE_WORKER_COUNT" -gt 0 ]; then
        echo -e "===== ORACLE WORKERS =====\n"
        for i in $(seq 1 $ORACLE_WORKER_COUNT); do
            container_name="masa_oracle_worker_$i"
            if docker ps -q -f name=$container_name >/dev/null 2>&1; then
                echo "Oracle Worker $i: Running"
            else
                echo "Oracle Worker $i: Not running or failed to start"
            fi
        done
        echo ""
    fi
    
    # Display TEE worker info if any running
    if [ "$TEE_WORKER_COUNT" -gt 0 ]; then
        echo -e "===== TEE WORKERS =====\n"
        for i in $(seq 1 $TEE_WORKER_COUNT); do
            container_name="masa_tee-worker_$i"
            if docker ps -q -f name=$container_name >/dev/null 2>&1; then
                echo "TEE Worker $i: Running"
            else 
                echo "TEE Worker $i: Not running or failed to start"
            fi
        done
        echo ""
    fi
    
    echo -e "============= End Node Information =============\n"
}

# Function to clean up containers
cleanup() {
    echo "Cleaning up containers..."
    docker rm -f $(docker ps -aq --filter "name=masa_") 2>/dev/null || echo "No containers to remove"
    echo "Done!"
}

# Clean up any existing containers
echo "Cleaning up existing containers..."
# First clean up all containers with masa_ prefix
docker ps -a | grep 'masa_' | awk '{print $1}' | xargs -r docker rm -f
# Also clean up any potential bootnode or oracle containers that might be running
docker ps -a | grep 'bootnode\|oracle\|worker' | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
# Ensure ports are released (give a little time for cleanup)
sleep 2

# Create masa_network if it doesn't exist
echo "Setting up Docker network..."
if ! docker network inspect masa_network >/dev/null 2>&1; then
    docker network create masa_network
fi

echo "Starting requested nodes:"
[ "$VALIDATOR_COUNT" -gt 0 ] && echo "- $VALIDATOR_COUNT validator(s)"
[ "$MINER_COUNT" -gt 0 ] && echo "- $MINER_COUNT miner(s)"
[ "$ENABLE_BOOTNODE" = "true" ] && echo "- 1 bootnode"
[ "$ORACLE_WORKER_COUNT" -gt 0 ] && echo "- $ORACLE_WORKER_COUNT oracle worker(s)"
[ "$TEE_WORKER_COUNT" -gt 0 ] && echo "- $TEE_WORKER_COUNT TEE worker(s)"

# Start validators
if [ "$VALIDATOR_COUNT" -gt 0 ]; then
    for i in $(seq 1 $VALIDATOR_COUNT); do
        echo "Starting validator $i..."
        start_node "validator" $i $VALIDATOR_PORT $VALIDATOR_METRICS_PORT $VALIDATOR_GRAFANA_PORT
    done
fi

# Start miners
if [ "$MINER_COUNT" -gt 0 ]; then
    for i in $(seq 1 $MINER_COUNT); do
        echo "Starting miner $i..."
        start_node "miner" $i $MINER_PORT $MINER_METRICS_PORT $MINER_GRAFANA_PORT
    done
fi

# Start bootnode if requested
BOOTNODE_ADDRESS=""
BOOTNODE_PEER_ID=${BOOTNODE_PEER_ID:-""}

if [ "$ENABLE_BOOTNODE" = "true" ]; then
    echo "Starting bootnode..."
    start_bootnode
    
    if [ "$ORACLE_WORKER_COUNT" -gt 0 ]; then
        if [ -n "$BOOTNODE_PEER_ID" ]; then
            # Use provided BOOTNODE_PEER_ID if specified
            echo "Using provided bootnode peer ID: $BOOTNODE_PEER_ID"
            BOOTNODE_ADDRESS="/ip4/$HOST_IP/udp/4001/quic-v1/p2p/$BOOTNODE_PEER_ID"
        else
            echo "Getting bootnode address for worker configuration..."
            # Get the bootnode address
            get_bootnode_address
            
            if [ -z "$BOOTNODE_ADDRESS" ] || [[ "$BOOTNODE_ADDRESS" != /* ]]; then
                echo "Warning: Failed to get valid bootnode address."
                echo "Options:"
                echo "1) Continue with basic bootstrap address (workers may not connect properly)"
                echo "2) Skip oracle worker setup (recommended to inspect bootnode logs first)"
                
                read -p "Enter your choice (1/2, default: 2): " choice
                choice=${choice:-2}
                
                case "$choice" in
                    1)
                        echo "Continuing with basic bootstrap address"
                        BOOTNODE_ADDRESS="/ip4/$HOST_IP/udp/4001/quic-v1"
                        ;;
                    *)
                        echo "Skipping oracle worker setup. You can manually inspect bootnode logs with:"
                        echo "docker logs masa_bootnode | grep -A 10 \"Multiaddresses:\""
                        ORACLE_WORKER_COUNT=0
                        ;;
                esac
            fi
        fi
    fi
fi

# Start oracle workers
if [ "$ORACLE_WORKER_COUNT" -gt 0 ]; then
    if [ "$ENABLE_BOOTNODE" = "true" ] && [ -n "$BOOTNODE_ADDRESS" ]; then
        for i in $(seq 1 $ORACLE_WORKER_COUNT); do
            echo "Starting oracle worker $i..."
            start_oracle_worker $i "$BOOTNODE_ADDRESS"
        done
    else
        echo "Warning: Cannot start oracle workers without a bootnode"
    fi
fi

# Start TEE workers
if [ "$TEE_WORKER_COUNT" -gt 0 ]; then
    for i in $(seq 1 $TEE_WORKER_COUNT); do
        echo "Starting TEE worker $i..."
        start_node "tee-worker" $i $TEE_WORKER_PORT $TEE_WORKER_METRICS_PORT $TEE_WORKER_GRAFANA_PORT
    done
fi

echo -e "\nActual running containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep masa_

# Wait a bit for logs to be available
sleep 5

# Display node information
display_node_info

echo "All nodes started. Check logs with:"
echo "docker logs -f masa_validator_N      # where N is the validator number"
echo "docker logs -f masa_miner_N          # where N is the miner number"
echo "docker logs -f masa_bootnode         # for the bootnode"
echo "docker logs -f masa_oracle_worker_N  # where N is the oracle worker number"
echo "docker logs -f masa_tee-worker_N     # where N is the TEE worker number" 

