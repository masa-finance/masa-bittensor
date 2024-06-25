#!/bin/bash

# Use environment variables for passwords
COLDKEY_PASSWORD=${COLDKEY_PASSWORD:-'default_coldkey_password'}
HOTKEY_PASSWORD=${HOTKEY_PASSWORD:-'default_hotkey_password'}

# Import run_faucet()
source run_faucet.sh

# Function to check if subnet 1 exists
check_subnet_exists() {
    local output
    output=$(btcli subnet list --subtensor.chain_endpoint ws://subtensor_machine:9945)
    echo "Current subnet list:"
    echo "$output"
    echo "$output" | awk 'NR>1 {print $1, $2}' | grep -q "*1 "
}


# Create and fund validator wallets
echo -e "$COLDKEY_PASSWORD\n$COLDKEY_PASSWORD" | btcli wallet new_coldkey --wallet.name validator --wallet.password
echo -e "$HOTKEY_PASSWORD\n$HOTKEY_PASSWORD" | btcli wallet new_hotkey --wallet.name validator --wallet.hotkey validator_hotkey --wallet.password

# Use the faucet for the validator wallet
run_faucet validator || { echo "Faucet failed for validator wallet"; exit 1; }
echo "Wallets for validator created, and faucet used successfully."

# Wait for subnet 1 to be created
echo "Waiting for subnet 1 to be created..."
while ! check_subnet_exists; do
    echo "Subnet 1 not found. Waiting 15 seconds before checking again..."
    sleep 15
done
echo "Subnet 1 has been created. Proceeding with registration."

# Function to register validator
register_validator() {
    local attempt=1
    local max_attempts=5

    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt to register validator..."
        
        output=$(btcli subnet register --wallet.name validator --wallet.hotkey validator_hotkey --subtensor.chain_endpoint ws://subtensor_machine:9946 2>&1)
        
        if echo "$output" | grep -q "Enter netuid \[0/1/3\] (0):"; then
            echo "1" | btcli subnet register --wallet.name validator --wallet.hotkey validator_hotkey --subtensor.chain_endpoint ws://subtensor_machine:9946 <<EOF
1
y
$COLDKEY_PASSWORD
y
EOF
            if [ $? -eq 0 ]; then
                echo "Successfully registered validator."
                return 0
            fi
        fi

        echo "Registration attempt failed. Waiting 15 seconds before retrying..."
        sleep 15
        ((attempt++))
    done

    echo "Failed to register validator after $max_attempts attempts."
    return 1
}

# Attempt to register the validator
register_validator

# Keep the container running
tail -f /dev/null
