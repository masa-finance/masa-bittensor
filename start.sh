#!/bin/bash

# Exit on error
set -e

# Colors and formatting
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Default timeout in seconds (10 minutes)
TIMEOUT=${TIMEOUT:-600}

# Default service counts if not set
MINER_COUNT=${MINER_COUNT:-1}
VALIDATOR_COUNT=${VALIDATOR_COUNT:-0}
LOGGING_DEBUG=${LOGGING_DEBUG:-false}

# Determine network details early
NETWORK=${NETWORK:-test}
if [ "$NETWORK" = "finney" ]; then
    NETWORK_DISPLAY="${RED}MAIN NETWORK (FINNEY)${NC}"
    NETUID="42"
else
    NETWORK_DISPLAY="${GREEN}TEST NETWORK${NC}"
    NETUID="165"
fi

# Validate required environment variables
validate_env() {
    if [ ! -f .env ]; then
        echo -e "${RED}Error: .env file not found${NC}"
        echo -e "Please create one from .env.sample:"
        echo -e "${YELLOW}cp .env.sample .env${NC}"
        return 1
    fi
    
    # Source .env file
    set -a
    source .env
    set +a
    
    return 0
}

# Function to check if a service is healthy
check_service_health() {
    local service=$1
    local service_status=$(docker service ls --filter name=$service --format "{{.Replicas}}" 2>/dev/null)
    
    if [ -z "$service_status" ]; then
        echo -e "${RED}Error: Service $service not found${NC}"
        return 1
    fi
    
    local current=$(echo $service_status | cut -d'/' -f1)
    local target=$(echo $service_status | cut -d'/' -f2)
    
    if [ "$current" != "$target" ]; then
        return 1
    fi
    return 0
}

# Always pull latest image before starting services
pull_latest_image() {
    echo -e "${BLUE}Pulling latest image from Docker Hub...${NC}"
    docker pull masaengineering/masa-bittensor:latest || {
        echo -e "${RED}Failed to pull latest image${NC}"
        return 1
    }
    echo -e "${GREEN}Successfully pulled latest image${NC}"
}

# Function to get service initialization status from logs
get_service_status() {
    local service=$1
    local logs=$(docker service logs $service --tail 100 2>/dev/null)
    
    # Check for container restarts first
    local restart_count=$(docker service ps $service --format "{{.Name}}: {{.CurrentState}}" 2>/dev/null | grep -c "Running\|Restarting")
    if [ "$restart_count" -gt 1 ]; then
        echo -e "${RED}Container restarting - Last error:${NC}"
        docker service logs $service --tail 20 2>/dev/null | grep -B2 -A5 "Error\|Exception\|Traceback" | head -n 8
        return
    fi
    
    # If no logs yet, check if containers are being created
    if [ -z "$logs" ]; then
        local tasks=$(docker service ps $service --format "{{.CurrentState}}" 2>/dev/null)
        if echo "$tasks" | grep -q "Preparing"; then
            echo "Creating container..."
        elif echo "$tasks" | grep -q "Starting"; then
            echo "Starting container..."
        elif echo "$tasks" | grep -q "Pending"; then
            echo "Waiting for resources..."
        else
            echo "Deploying service..."
        fi
        return
    fi
    
    # Check for common error conditions first
    if echo "$logs" | grep -q "Error: \|Exception\|Traceback"; then
        echo -e "${RED}Error detected:${NC}"
        docker service logs $service --tail 20 2>/dev/null | grep -B2 -A5 "Error\|Exception\|Traceback" | head -n 8
        return
    fi
    
    # Check for specific initialization states
    if echo "$logs" | grep -q "Loading coldkey"; then
        echo "Loading wallet keys..."
    elif echo "$logs" | grep -q "Generating new coldkey"; then
        echo "Generating new wallet..."
    elif echo "$logs" | grep -q "Registering wallet"; then
        echo "Registering with subnet $NETUID..."
    elif echo "$logs" | grep -q "Waiting for registration"; then
        # Try to get more specific registration status
        if echo "$logs" | grep -q "Registration pending"; then
            echo "Registration pending approval..."
        else
            echo "Waiting for registration confirmation..."
        fi
    elif echo "$logs" | grep -q "Starting mining"; then
        # Check for specific mining states
        if echo "$logs" | grep -q "Connecting to network"; then
            echo "Connecting to Bittensor network..."
        elif echo "$logs" | grep -q "Syncing with subnet"; then
            echo "Syncing with subnet $NETUID..."
        else
            echo "Starting mining process..."
        fi
    elif echo "$logs" | grep -q "Starting validation"; then
        # Check for specific validation states
        if echo "$logs" | grep -q "Loading model"; then
            echo "Loading validation model..."
        elif echo "$logs" | grep -q "Connecting to miners"; then
            echo "Connecting to miners..."
        else
            echo "Starting validation process..."
        fi
    elif echo "$logs" | grep -q "Python path"; then
        echo "Initializing Python environment..."
    elif echo "$logs" | grep -q "ImportError\|ModuleNotFoundError"; then
        echo "Loading Python dependencies..."
    elif echo "$logs" | grep -q "Traceback"; then
        # Get the actual error message
        local error=$(echo "$logs" | grep -A 1 "Traceback" | tail -n1)
        echo "Error: ${error}"
    else
        # Check container state if no specific status found
        local state=$(docker service ps $service --format "{{.CurrentState}}" 2>/dev/null | head -n1)
        if [ -n "$state" ]; then
            echo "Container state: $state..."
        else
            echo "Starting up..."
        fi
    fi
}

# Monitor registration status
monitor_registration() {
    echo -e "\n${BLUE}Monitoring registration status...${NC}"
    echo -e "${YELLOW}This may take a few minutes while nodes register with the network${NC}\n"

    local MAX_ATTEMPTS=30
    local ATTEMPT=0
    local last_status=""
    local consecutive_failures=0
    
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        # Check service health first
        if ! check_service_health masa_miner; then
            consecutive_failures=$((consecutive_failures + 1))
            if [ $consecutive_failures -ge 3 ]; then
                echo -e "${RED}Error: Services appear to be unhealthy. Please check logs:${NC}"
                echo -e "${YELLOW}docker service logs masa_miner${NC}"
                return 1
            fi
            sleep 10
            continue
        fi
        consecutive_failures=0
        
        # Run the report script with timeout
        if ! timeout 30s python startup/report.py 0 > /tmp/report_output 2>&1; then
            echo -e "${YELLOW}Warning: Report script timed out, retrying...${NC}"
            sleep 5
            continue
        fi
        
        local OUTPUT=$(cat /tmp/report_output)
        
        # Extract registration info
        local miner_reg=$(echo "$OUTPUT" | grep -A2 "⛏️  Miner Status" | grep "Registration:" || echo "Unknown")
        local validator_reg=$(echo "$OUTPUT" | grep -A2 "🔍 Validator Status" | grep "Registration:" || echo "Unknown")
        
        # Show registration status
        echo -e "\n[Attempt ${ATTEMPT}/${MAX_ATTEMPTS}] Checking registrations..."
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
        
        # Check if all services are registered
        if echo "$OUTPUT" | grep -q "✅ All services are running and registered successfully!"; then
            REGISTERED=true
            return 0
        fi
        
        ATTEMPT=$((ATTEMPT + 1))
        sleep 10
    done

    return 1
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    docker stack rm masa 2>/dev/null || true
    rm -f /tmp/report_output 2>/dev/null || true
}

# Main deployment section
main() {
    echo -e "${BOLD}Starting Masa Bittensor Subnet Services${NC}"
    echo -e "Network: $NETWORK_DISPLAY"
    echo -e "Subnet ID: ${YELLOW}$NETUID${NC}"
    echo -e "Deploying: ${GREEN}$VALIDATOR_COUNT validators${NC}, ${GREEN}$MINER_COUNT miners${NC}"
    echo

    # Validate environment
    validate_env || exit 1

    # Pull latest image
    pull_latest_image || exit 1

    # Initialize Docker swarm if not already done
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

    # Set up image name
    IMAGE_TO_USE=${DOCKER_IMAGE:-masaengineering/masa-bittensor:latest}
    echo -e "\nUsing image: ${GREEN}${IMAGE_TO_USE}${NC}"

    # Deploy stack
    echo -e "\n${BLUE}Deploying stack...${NC}"
    
    # Remove any existing stack
    docker stack rm masa >/dev/null 2>&1 || true
    sleep 2
    
    # Deploy new stack
    DOCKER_IMAGE=$IMAGE_TO_USE docker stack deploy -c docker-compose.yml masa || {
        echo -e "${RED}Failed to deploy stack${NC}"
        exit 1
    }

    echo -e "\n${YELLOW}Services are starting up - this process includes:${NC}"
    echo -e "1. Container creation"
    echo -e "2. Loading or generating wallet keys"
    echo -e "3. Registering with subnet $NETUID"
    echo -e "4. Starting mining/validation processes\n"

    # Monitor deployment
    local start_time=$(date +%s)
    local last_status=""
    local error_count=0
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $TIMEOUT ]; then
            echo -e "\n${RED}❌ Timeout waiting for services to start${NC}"
            echo -e "\nLast errors from services:"
            docker service logs masa_miner --tail 50 2>/dev/null | grep -B2 -A5 "Error\|Exception\|Traceback"
            docker service logs masa_validator --tail 50 2>/dev/null | grep -B2 -A5 "Error\|Exception\|Traceback"
            exit 1
        fi

        # Get current counts and status
        local miner_count=$(docker service ls --filter name=masa_miner --format "{{.Replicas}}" | grep -o "[0-9]*/[0-9]*" | cut -d "/" -f 1)
        local validator_count=$(docker service ls --filter name=masa_validator --format "{{.Replicas}}" | grep -o "[0-9]*/[0-9]*" | cut -d "/" -f 1)
        local miner_init_status=$(get_service_status masa_miner)
        local validator_init_status=$(get_service_status masa_validator)
        
        # Check for errors in status
        if echo "$miner_init_status$validator_init_status" | grep -q "Error\|Exception\|Traceback"; then
            error_count=$((error_count + 1))
            if [ $error_count -ge 3 ]; then
                echo -e "\n${RED}❌ Services are failing to start properly${NC}"
                echo -e "\nMiner Status:"
                docker service ps masa_miner
                echo -e "\nValidator Status:"
                docker service ps masa_validator
                echo -e "\nUse these commands for more details:"
                echo -e "${YELLOW}docker service logs masa_miner${NC}"
                echo -e "${YELLOW}docker service logs masa_validator${NC}"
                exit 1
            fi
        else
            error_count=0
        fi
        
        # Create status message
        local status="[${elapsed}s] Current Status:"
        status+="\n   📦 Miners ($miner_count/$MINER_COUNT): ${YELLOW}$miner_init_status${NC}"
        status+="\n   🔍 Validators ($validator_count/$VALIDATOR_COUNT): ${YELLOW}$validator_init_status${NC}"
        
        # Update status if changed
        if [ "$status" != "$last_status" ]; then
            echo -e "$status"
            last_status="$status"
        fi
        
        # Check if services are ready
        if [ "$miner_count" -eq "$MINER_COUNT" ] && [ "$validator_count" -eq "$VALIDATOR_COUNT" ]; then
            if echo "$miner_init_status" | grep -q "Starting mining" && \
               ([ "$VALIDATOR_COUNT" -eq 0 ] || echo "$validator_init_status" | grep -q "Starting validation"); then
                echo -e "\n${GREEN}✅ All services are running and initialized!${NC}"
                break
            fi
        fi
        
        sleep 5
    done

    # Monitor registration
    if monitor_registration; then
        echo -e "\n${GREEN}🎉 Setup Complete!${NC}"
        echo -e "\nTo monitor your nodes:"
        echo -e "• View logs: ${YELLOW}docker service logs masa_miner -f${NC}"
        echo -e "• Check status: ${YELLOW}python startup/report.py${NC}"
    else
        echo -e "\n${YELLOW}⚠️  Setup completed but some services may still be initializing${NC}"
        echo -e "Run ${YELLOW}python startup/report.py${NC} later to check the status"
        echo -e "View logs with: ${YELLOW}docker service logs masa_miner -f${NC}"
    fi
}

# Set up cleanup trap
trap cleanup EXIT

# Run main function
main "$@" 