#!/bin/bash

# Activate the virtual environment
source /opt/bittensor-venv/bin/activate

# Use environment variables for passwords
COLDKEY_PASSWORD=${COLDKEY_PASSWORD:-'default_coldkey_password'}
HOTKEY_PASSWORD=${HOTKEY_PASSWORD:-'default_hotkey_password'}

# Import the shared functions
source functions.sh

# Function to check if validator is ready
check_validator_ready() {
    local max_attempts=180  # 15 minutes (180 * 5 seconds)
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" http://validator_machine:8000/ | grep -qE "^[2-5][0-9][0-9]$"; then
            echo "Validator is ready."
            return 0
        fi
        attempt=$((attempt+1))
        echo "Validator not ready. Attempt $attempt of $max_attempts. Waiting 5 seconds..."
        sleep 5
    done
    echo "Validator did not become ready within the timeout period."
    return 1
}

# Create and fund miner wallets
#
# Create a new coldkey with the specified password
echo -e "$COLDKEY_PASSWORD\n$COLDKEY_PASSWORD" | btcli wallet new_coldkey --wallet.name miner --wallet.password

# Create a new hotkey with the specified password
echo -e "$HOTKEY_PASSWORD\n$HOTKEY_PASSWORD" | btcli wallet new_hotkey --wallet.name miner --wallet.hotkey miner_hotkey --wallet.password

# Use the faucet for the miner wallet
run_faucet miner || { echo "Faucet failed for miner wallet"; exit 1; }

echo "Wallets for miner created, and faucet used successfully."

# Wait for subnet 1 to be created
echo "Waiting for subnet 1 to be created..."
while ! check_subnet_exists; do
    echo "Subnet 1 not found. Waiting 15 seconds before checking again..."
    sleep 15
done
echo "Subnet 1 has been created. Proceeding with registration."

# Wait for validator to be ready
echo "Waiting for validator to be ready..."
if check_validator_ready; then
    echo "Validator is ready. Proceeding with miner registration."
else
    echo "Validator did not become ready within the timeout period. Exiting."
    exit 1
fi

# Attempt to register the validator and start it
if register_node miner; then
    echo "Miner registration successful. Starting the miner..."
    # Start the miner
    python /app/neurons/miner.py --netuid 1 --subtensor.chain_endpoint ws://subtensor_machine:9946 --wallet.name miner --wallet.hotkey miner_hotkey --axon.port 8091
else
    echo "Miner registration failed. Not starting the validator."
fi

deactivate

tail -f /dev/null
