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
REPORT_TIMEOUT=${REPORT_TIMEOUT:-60}
CLEANUP_ON_FAILURE=${CLEANUP_ON_FAILURE:-false}

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
    
    echo -e "\n${BLUE}Status for $service:${NC}"
    
    # Show service details
    echo -e "\n${YELLOW}Service Details:${NC}"
    docker service ps $service --no-trunc --format "ID: {{.ID}}\nName: {{.Name}}\nImage: {{.Image}}\nNode: {{.Node}}\nState: {{.CurrentState}}\nError: {{.Error}}\n"
    
    # Show recent logs with timestamps
    echo -e "\n${YELLOW}Recent Logs:${NC}"
    docker service logs --timestamps --tail 50 $service 2>&1 || {
        echo -e "${RED}No logs available yet${NC}"
    }
    
    # Show any errors or warnings specifically
    echo -e "\n${YELLOW}Errors/Warnings (if any):${NC}"
    docker service logs --timestamps $service 2>&1 | grep -i "error\|warning\|critical\|failed\|exception\|traceback" || {
        echo -e "${GREEN}No errors found in logs${NC}"
    }
}

# Monitor registration status
monitor_registration() {
    echo -e "\n${BLUE}Monitoring registration status...${NC}"
    echo -e "${YELLOW}This may take a few minutes while nodes register with the network${NC}\n"

    local MAX_ATTEMPTS=30
    local ATTEMPT=0
    local consecutive_failures=0
    
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        echo -e "\n[Attempt ${ATTEMPT}/${MAX_ATTEMPTS}] Checking registrations..."
        
        # Check services health first
        local services_healthy=true
        local all_registered=true
        
        if [ "$VALIDATOR_COUNT" -gt 0 ]; then
            if ! check_service_health masa_validator; then
                services_healthy=false
                consecutive_failures=$((consecutive_failures + 1))
                if [ $consecutive_failures -ge 3 ]; then
                    echo -e "${RED}Error: Validator service appears to be unhealthy. Please check logs:${NC}"
                    get_service_status masa_validator
                    return 1
                fi
            else
                # Check registration status from logs
                local validator_logs=$(docker service logs masa_validator 2>&1)
                if echo "$validator_logs" | grep -q "Hotkey is registered with UID"; then
                    echo -e "  Validators: ${GREEN}✓${NC} Registered"
                else
                    all_registered=false
                    echo -e "  Validators: ${YELLOW}⏳${NC} Not registered yet"
                    # Show any errors
                    echo "$validator_logs" | grep -i "error\|warning\|critical\|failed\|exception\|traceback" || true
                fi
            fi
        fi
        
        if [ "$MINER_COUNT" -gt 0 ]; then
            if ! check_service_health masa_miner; then
                services_healthy=false
                consecutive_failures=$((consecutive_failures + 1))
                if [ $consecutive_failures -ge 3 ]; then
                    echo -e "${RED}Error: Miner service appears to be unhealthy. Please check logs:${NC}"
                    get_service_status masa_miner
                    return 1
                fi
            else
                # Check registration status from logs
                local miner_logs=$(docker service logs masa_miner 2>&1)
                if echo "$miner_logs" | grep -q "Hotkey is registered with UID"; then
                    echo -e "  Miners: ${GREEN}✓${NC} Registered"
                else
                    all_registered=false
                    echo -e "  Miners: ${YELLOW}⏳${NC} Not registered yet"
                    # Show any errors
                    echo "$miner_logs" | grep -i "error\|warning\|critical\|failed\|exception\|traceback" || true
                fi
            fi
        fi
        
        if ! $services_healthy; then
            sleep 10
            continue
        fi
        
        consecutive_failures=0
        
        if $all_registered; then
            echo -e "\n${GREEN}✅ All services are running and registered successfully!${NC}"
            return 0
        fi
        
        ATTEMPT=$((ATTEMPT + 1))
        sleep 10
    done

    echo -e "${RED}Registration monitoring timed out after ${MAX_ATTEMPTS} attempts${NC}"
    return 1
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    docker stack rm masa 2>/dev/null || true
}

# Monitor deployment
monitor_deployment() {
    echo -e "\n${BLUE}Monitoring deployment...${NC}"
    local start_time=$(date +%s)
    local elapsed=0
    local first_check=true

    while [ $elapsed -lt $TIMEOUT ]; do
        # Always show status on first check
        if $first_check; then
            echo -e "\n${YELLOW}Initial service status:${NC}"
            if [ "$VALIDATOR_COUNT" -gt 0 ]; then
                get_service_status masa_validator
            fi
            if [ "$MINER_COUNT" -gt 0 ]; then
                get_service_status masa_miner
            fi
            first_check=false
            sleep 5
            continue
        fi

        # Check if services are running
        local all_running=true
        
        # Check validator service if replicas > 0
        if [ "$VALIDATOR_COUNT" -gt 0 ] && ! check_service_health masa_validator; then
            all_running=false
            get_service_status masa_validator
        fi
        
        # Check miner service if replicas > 0
        if [ "$MINER_COUNT" -gt 0 ] && ! check_service_health masa_miner; then
            all_running=false
            get_service_status masa_miner
        fi

        if $all_running; then
            echo -e "${GREEN}All services are running${NC}"
            # Show final status
            echo -e "\n${YELLOW}Final service status:${NC}"
            if [ "$VALIDATOR_COUNT" -gt 0 ]; then
                get_service_status masa_validator
            fi
            if [ "$MINER_COUNT" -gt 0 ]; then
                get_service_status masa_miner
            fi
            break
        fi

        # Update elapsed time
        elapsed=$(($(date +%s) - start_time))
        echo -e "\n${YELLOW}Time elapsed: ${elapsed}s / ${TIMEOUT}s${NC}"
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
    echo -e "Cleanup on failure: ${CLEANUP_ON_FAILURE}"
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

    # Monitor deployment
    if ! monitor_deployment; then
        echo -e "${RED}Deployment monitoring failed or timed out${NC}"
        if [ "$CLEANUP_ON_FAILURE" = "true" ]; then
            cleanup
        fi
        exit 1
    fi

    # Monitor registration
    if ! monitor_registration; then
        echo -e "${RED}Registration monitoring failed or timed out${NC}"
        if [ "$CLEANUP_ON_FAILURE" = "true" ]; then
            cleanup
        fi
        exit 1
    fi

    echo -e "\n${GREEN}Deployment completed successfully!${NC}"
    exit 0
}

# Set up cleanup trap
trap cleanup EXIT

# Run main function
main "$@" 
