#!/bin/bash

# Colors and formatting
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "\n${BLUE}=== 🚀 Starting MASA Bittensor Stack ===${NC}\n"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo -e "Please create one from .env.sample:"
    echo -e "${YELLOW}cp .env.sample .env${NC}"
    exit 1
fi

# Source .env file
set -a
source .env
set +a

echo -e "${BLUE}Configuration:${NC}"
echo -e "• Miners: ${GREEN}${MINER_COUNT:-1}${NC}"
echo -e "• Validators: ${GREEN}${VALIDATOR_COUNT:-0}${NC}"
echo -e "• Network: ${GREEN}${NETWORK:-finney}${NC}"

# Initialize swarm if needed
if ! docker node ls > /dev/null 2>&1; then
    echo -e "\n${YELLOW}Initializing Docker Swarm...${NC}"
    docker swarm init > /dev/null 2>&1 || {
        echo -e "${RED}Failed to initialize Docker Swarm${NC}"
        exit 1
    }
    echo -e "${GREEN}✓${NC} Swarm initialized"
else
    echo -e "\n${GREEN}✓${NC} Swarm already initialized"
fi

# Function to wait for service readiness
wait_for_services() {
    local timeout=300  # 5 minutes timeout
    local start_time=$(date +%s)
    
    echo -e "\n${BLUE}Waiting for services to start...${NC}"
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            echo -e "${RED}Timeout waiting for services${NC}"
            exit 1
        fi
        
        # Get service status
        local miner_status=$(docker service ls --format '{{.Name}} {{.Replicas}}' | grep masa_miner || echo "")
        local validator_status=$(docker service ls --format '{{.Name}} {{.Replicas}}' | grep masa_validator || echo "")
        
        # Check if services are ready
        if [[ $miner_status == *"$MINER_COUNT/$MINER_COUNT"* ]] && \
           [[ $validator_status == *"$VALIDATOR_COUNT/$VALIDATOR_COUNT"* ]]; then
            echo -e "${GREEN}✓${NC} All services started"
            return 0
        fi
        
        echo -n "."
        sleep 5
    done
}

# Deploy the stack
echo -e "\n${BLUE}Deploying stack...${NC}"

if [ -n "$DOCKER_IMAGE" ]; then
    echo -e "Using image: ${GREEN}${DOCKER_IMAGE}${NC}"
else
    echo -e "Using image: ${GREEN}masaengineering/masa-bittensor:latest${NC}"
fi

docker stack deploy -c docker-compose.yml masa

# Wait for services to start
wait_for_services

# Monitor registration status
echo -e "\n${BLUE}Monitoring registration status...${NC}"
echo -e "${YELLOW}This may take a few minutes...${NC}\n"

MAX_ATTEMPTS=30
ATTEMPT=0
REGISTERED=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    # Run the report script
    OUTPUT=$(python startup/report.py 0)
    
    # Check if all services are registered
    if echo "$OUTPUT" | grep -q "✅ All services are running and registered successfully!"; then
        REGISTERED=true
        break
    fi
    
    # Show progress
    echo -n "."
    ATTEMPT=$((ATTEMPT + 1))
    sleep 10
done

echo -e "\n\n${BLUE}=== Final Status ===${NC}\n"
python startup/report.py 0

if [ "$REGISTERED" = true ]; then
    echo -e "\n${GREEN}🎉 Setup Complete!${NC}"
    echo -e "\nTo monitor your nodes:"
    echo -e "• View logs: ${YELLOW}docker service logs masa_miner -f${NC}"
    echo -e "• Check status: ${YELLOW}python startup/report.py${NC}"
else
    echo -e "\n${YELLOW}⚠️  Setup completed but some services may still be initializing${NC}"
    echo -e "Run ${YELLOW}python startup/report.py${NC} later to check the status"
fi 