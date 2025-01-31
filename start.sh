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

# Default configuration
VALIDATOR_COUNT=${VALIDATOR_COUNT:-0}
MINER_COUNT=${MINER_COUNT:-1}
NETWORK=${NETWORK:-test}
LOGGING_DEBUG=${LOGGING_DEBUG:-false}

# Determine network details early
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
    local restart_info=$(docker service ps $service --format "{{.Name}} {{.CurrentState}} {{.Error}}" 2>/dev/null)
    local restart_count=$(echo "$restart_info" | grep -c "Running\|Restarting")
    
    if [ "$restart_count" -gt 1 ]; then
        echo -e "${RED}Container restarting - History:${NC}"
        docker service ps $service --no-trunc --format "{{.Error}}" | grep -v "^$" | head -n 3
        echo -e "${RED}Last error from logs:${NC}"
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
        # Check services health first
        local services_healthy=true
        
        if [ "$VALIDATOR_COUNT" -gt 0 ] && ! check_service_health masa_validator; then
            services_healthy=false
            consecutive_failures=$((consecutive_failures + 1))
            if [ $consecutive_failures -ge 3 ]; then
                echo -e "${RED}Error: Validator service appears to be unhealthy. Please check logs:${NC}"
                echo -e "${YELLOW}docker service logs masa_validator${NC}"
                return 1
            fi
            sleep 10
            continue
        fi
        
        if [ "$MINER_COUNT" -gt 0 ] && ! check_service_health masa_miner; then
            services_healthy=false
            consecutive_failures=$((consecutive_failures + 1))
            if [ $consecutive_failures -ge 3 ]; then
                echo -e "${RED}Error: Miner service appears to be unhealthy. Please check logs:${NC}"
                echo -e "${YELLOW}docker service logs masa_miner${NC}"
                return 1
            fi
            sleep 10
            continue
        fi
        
        if $services_healthy; then
            consecutive_failures=0
        fi
        
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
        
        if [ "$MINER_COUNT" -gt 0 ]; then
            if [[ $miner_reg == *"Registered"* ]]; then
                echo -e "  Miners: ${GREEN}✓${NC} Registered"
            elif [[ $miner_reg == *"Not Registered"* ]]; then
                echo -e "  Miners: ${YELLOW}⏳${NC} Not registered yet"
            fi
        fi
        
        if [ "$VALIDATOR_COUNT" -gt 0 ]; then
            if [[ $validator_reg == *"Registered"* ]]; then
                echo -e "  Validators: ${GREEN}✓${NC} Registered"
            elif [[ $validator_reg == *"Not Registered"* ]]; then
                echo -e "  Validators: ${YELLOW}⏳${NC} Not registered yet"
            fi
        fi
        
        # Check if all required services are registered
        local all_registered=true
        
        if [ "$MINER_COUNT" -gt 0 ] && [[ ! $miner_reg == *"Registered"* ]]; then
            all_registered=false
        fi
        
        if [ "$VALIDATOR_COUNT" -gt 0 ] && [[ ! $validator_reg == *"Registered"* ]]; then
            all_registered=false
        fi
        
        if $all_registered; then
            echo -e "\n${GREEN}✅ All services are running and registered successfully!${NC}"
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

# Monitor deployment
monitor_deployment() {
    echo -e "\n${BLUE}Monitoring deployment...${NC}"
    local start_time=$(date +%s)
    local elapsed=0

    while [ $elapsed -lt $TIMEOUT ]; do
        # Check if services are running
        local all_running=true
        
        # Check validator service if replicas > 0
        if [ "$VALIDATOR_COUNT" -gt 0 ] && ! check_service_health masa_validator; then
            all_running=false
            echo -e "\n${BLUE}Status for validator:${NC}"
            get_service_status masa_validator
        fi
        
        # Check miner service if replicas > 0
        if [ "$MINER_COUNT" -gt 0 ] && ! check_service_health masa_miner; then
            all_running=false
            echo -e "\n${BLUE}Status for miner:${NC}"
            get_service_status masa_miner
        fi

        if $all_running; then
            echo -e "${GREEN}All services are running${NC}"
            break
        fi

        # Update elapsed time
        elapsed=$(($(date +%s) - start_time))
        sleep 10
    done

    if [ $elapsed -ge $TIMEOUT ]; then
        echo -e "${RED}Deployment timed out after ${TIMEOUT} seconds${NC}"
        return 1
    fi

    return 0
}

# Main deployment section
main() {
    echo -e "${BOLD}Starting Masa Bittensor Subnet Services${NC}"
    echo -e "Network: $NETWORK_DISPLAY"
    echo -e "Subnet ID: ${YELLOW}$NETUID${NC}"
    echo -e "Deploying: ${GREEN}$MINER_COUNT miners and $VALIDATOR_COUNT validators${NC}"
    echo

    # Validate environment
    validate_env || exit 1

    # Pull latest image
    pull_latest_image || exit 1

    echo -e "\n${BLUE}Deploying stack...${NC}"
    if ! docker stack deploy -c docker-compose.yml masa; then
        echo -e "${RED}Failed to deploy stack${NC}"
        exit 1
    fi

    # Wait a moment for services to be created
    sleep 5

    # Check for immediate failures
    for service in masa_neuron; do
        if docker service ps $service --format "{{.Error}}" 2>/dev/null | grep -q .; then
            echo -e "${RED}Service $service failed to start. Logs:${NC}"
            docker service ps $service --no-trunc --format "{{.Error}}" | grep -v "^$"
            echo -e "\n${YELLOW}Container logs:${NC}"
            docker service logs $service 2>&1 || true
            cleanup
            exit 1
        fi
    done

    # Monitor deployment
    echo -e "\n${BLUE}Monitoring deployment...${NC}"
    local start_time=$(date +%s)
    local elapsed=0

    while [ $elapsed -lt $TIMEOUT ]; do
        # Check if services are running
        local all_running=true
        
        # Check validator service if replicas > 0
        if [ "$VALIDATOR_COUNT" -gt 0 ] && ! check_service_health masa_validator; then
            all_running=false
            echo -e "\n${BLUE}Status for validator:${NC}"
            get_service_status masa_validator
        fi
        
        # Check miner service if replicas > 0
        if [ "$MINER_COUNT" -gt 0 ] && ! check_service_health masa_miner; then
            all_running=false
            echo -e "\n${BLUE}Status for miner:${NC}"
            get_service_status masa_miner
        fi

        if $all_running; then
            echo -e "${GREEN}All services are running${NC}"
            break
        fi

        # Update elapsed time
        elapsed=$(($(date +%s) - start_time))
        sleep 10
    done

    if [ $elapsed -ge $TIMEOUT ]; then
        echo -e "${RED}Deployment timed out after ${TIMEOUT} seconds${NC}"
        cleanup
        exit 1
    fi

    # Continue with registration monitoring if deployment succeeded
    if ! monitor_registration; then
        echo -e "${RED}Registration monitoring failed or timed out${NC}"
        cleanup
        exit 1
    fi

    echo -e "\n${GREEN}Deployment completed successfully!${NC}"
    return 0
}

# Set up cleanup trap
trap cleanup EXIT

# Run main function
main "$@" 
