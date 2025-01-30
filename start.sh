#!/bin/bash

# Colors and formatting
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Determine network details
NETWORK=${NETWORK:-test}
if [ "$NETWORK" = "finney" ]; then
    NETWORK_DISPLAY="${RED}MAIN NETWORK (FINNEY)${NC}"
    NETUID="42"
    echo -e "\n${RED}⚠️  WARNING: You are connecting to the MAIN NETWORK${NC}"
    echo -e "${RED}    This will use real TAO. Are you sure? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Aborting. Set NETWORK=test in .env to use the test network${NC}"
        exit 1
    fi
else
    NETWORK_DISPLAY="${GREEN}TEST NETWORK${NC}"
    NETUID="165"
fi

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
echo -e "• Network: ${NETWORK_DISPLAY}"
echo -e "• Subnet: ${GREEN}${NETUID}${NC}"
echo -e "• Miners: ${GREEN}${MINER_COUNT:-1}${NC}"
echo -e "• Validators: ${GREEN}${VALIDATOR_COUNT:-0}${NC}"

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
    local last_status=""
    
    echo -e "\n${BLUE}Waiting for services to start...${NC}"
    echo -e "${YELLOW}Target: ${MINER_COUNT} miners, ${VALIDATOR_COUNT} validators${NC}\n"
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        local elapsed_min=$((elapsed / 60))
        local elapsed_sec=$((elapsed % 60))
        
        if [ $elapsed -gt $timeout ]; then
            echo -e "\n${RED}Timeout waiting for services${NC}"
            echo -e "Check logs with: ${YELLOW}docker service logs masa_miner${NC}"
            exit 1
        fi
        
        # Get service status
        local miner_status=$(docker service ls --format '{{.Name}} {{.Replicas}}' | grep masa_miner || echo "")
        local validator_status=$(docker service ls --format '{{.Name}} {{.Replicas}}' | grep masa_validator || echo "")
        
        # Parse current counts
        local miner_current=$(echo $miner_status | grep -o '[0-9]*/[0-9]*' | cut -d/ -f1 || echo "0")
        local miner_target=$(echo $miner_status | grep -o '[0-9]*/[0-9]*' | cut -d/ -f2 || echo "0")
        local validator_current=$(echo $validator_status | grep -o '[0-9]*/[0-9]*' | cut -d/ -f1 || echo "0")
        local validator_target=$(echo $validator_status | grep -o '[0-9]*/[0-9]*' | cut -d/ -f2 || echo "0")
        
        # Prepare status message
        local status_msg="[${elapsed_min}m${elapsed_sec}s] "
        status_msg+="Miners: ${miner_current}/${miner_target}, "
        status_msg+="Validators: ${validator_current}/${validator_target}"
        
        # Only print if status changed
        if [ "$status_msg" != "$last_status" ]; then
            echo -e "\r\033[K${status_msg}"  # Clear line and print new status
            last_status="$status_msg"
        fi
        
        # Check if services are ready
        if [[ $miner_status == *"$MINER_COUNT/$MINER_COUNT"* ]] && \
           [[ $validator_status == *"$VALIDATOR_COUNT/$VALIDATOR_COUNT"* ]]; then
            echo -e "\n${GREEN}✓${NC} All services started successfully"
            return 0
        fi
        
        sleep 2
    done
}

# Monitor registration status
monitor_registration() {
    echo -e "\n${BLUE}Monitoring registration status...${NC}"
    echo -e "${YELLOW}This may take a few minutes while nodes register with the network${NC}\n"

    MAX_ATTEMPTS=30
    ATTEMPT=0
    REGISTERED=false
    local last_status=""

    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        # Run the report script
        OUTPUT=$(python startup/report.py 0)
        
        # Extract registration info
        local miner_reg=$(echo "$OUTPUT" | grep -A2 "⛏️  Miner Status" | grep "Registration:" || echo "Unknown")
        local validator_reg=$(echo "$OUTPUT" | grep -A2 "🔍 Validator Status" | grep "Registration:" || echo "Unknown")
        
        # Prepare status message
        local status_msg="[Attempt ${ATTEMPT}/${MAX_ATTEMPTS}] "
        status_msg+="Checking registrations..."
        
        # Only print if status changed
        if [ "$status_msg" != "$last_status" ]; then
            echo -e "\r\033[K${status_msg}"  # Clear line and print new status
            
            # Show registration status if available
            if [[ $miner_reg == *"Registered"* ]]; then
                echo -e "  Miners: ${GREEN}✓${NC} Registered"
            elif [[ $miner_reg == *"Not Registered"* ]]; then
                echo -e "  Miners: ${YELLOW}⏳${NC} Not registered yet"
            fi
            
            if [[ $validator_reg == *"Registered"* ]]; then
                echo -e "  Validators: ${GREEN}✓${NC} Registered"
            elif [[ $validator_reg == *"Not Registered"* ]]; then
                echo -e "  Validators: ${YELLOW}⏳${NC} Not registered yet"
            fi
            
            last_status="$status_msg"
        fi
        
        # Check if all services are registered
        if echo "$OUTPUT" | grep -q "✅ All services are running and registered successfully!"; then
            REGISTERED=true
            break
        fi
        
        ATTEMPT=$((ATTEMPT + 1))
        sleep 10
    done

    return 0
}

# Deploy the stack
echo -e "\n${BLUE}Deploying stack...${NC}"

if [ -n "$DOCKER_IMAGE" ]; then
    echo -e "Using image: ${GREEN}${DOCKER_IMAGE}${NC}"
    IMAGE_TO_USE=$DOCKER_IMAGE
else
    IMAGE_TO_USE="masaengineering/masa-bittensor:latest"
    echo -e "Using image: ${GREEN}${IMAGE_TO_USE}${NC}"
fi

# Try to pull the image first
echo -e "\n${BLUE}Pulling image...${NC}"
if docker pull $IMAGE_TO_USE; then
    echo -e "${GREEN}✓${NC} Image pulled successfully"
else
    echo -e "${YELLOW}⚠️  Could not pull image. Trying to build locally...${NC}"
    if docker compose build; then
        echo -e "${GREEN}✓${NC} Local build successful"
        IMAGE_TO_USE="masa-bittensor:latest"
    else
        echo -e "${RED}Error: Failed to pull or build image${NC}"
        exit 1
    fi
fi

# Deploy with the image we got
DOCKER_IMAGE=$IMAGE_TO_USE docker stack deploy -c docker-compose.yml masa

# Wait for services to start
wait_for_services

# Monitor registration
monitor_registration

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
    echo -e "View logs with: ${YELLOW}docker service logs masa_miner -f${NC}"
fi 