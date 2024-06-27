#!/bin/bash

# Activate the virtual environment
source /opt/bittensor-venv/bin/activate

# Use environment variables for passwords
COLDKEY_PASSWORD=${COLDKEY_PASSWORD:-'default_coldkey_password'}
HOTKEY_PASSWORD=${HOTKEY_PASSWORD:-'default_hotkey_password'}
ORACLE_BASE_URL="http://34.72.224.59:8080/api/v1"

# Import the shared functions
source functions.sh

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

docker_self_IP=$(getent hosts miner_machine | awk '{ print $1 }')

# Attempt to register the miner and start it
if register_node miner; then
    echo "Miner registration successful. Starting the miner..."
    # Start the miner
    # Set ORACLE_BASE_URL to the masa protocol (oracle) node the miner uses
    ORACLE_BASE_URL=$ORACLE_BASE_URL; python /app/neurons/miner.py --netuid 1 --subtensor.chain_endpoint ws://subtensor_machine:9946 --wallet.name miner --wallet.hotkey miner_hotkey --axon.external_ip "$docker_self_IP" --axon.port 8093
else
    echo "Miner registration failed. Not starting the validator."
fi

deactivate

tail -f /dev/null