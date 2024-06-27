#!/bin/bash

# Activate the virtual environment
source /opt/bittensor-venv/bin/activate

# Use environment variables for passwords
COLDKEY_PASSWORD=${COLDKEY_PASSWORD:-'default_coldkey_password'}
HOTKEY_PASSWORD=${HOTKEY_PASSWORD:-'default_hotkey_password'}
# Import shared functions
source functions.sh

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

echo "Wait 30s for miner to register and start"
sleep 30

echo"Register validator on the root subnet."
echo "1" | btcli root register --wallet.name validator --wallet.hotkey validator_hotkey --subtensor.chain_endpoint ws://subtensor_machine:9945 <<EOF
$COLDKEY_PASSWORD
y
EOF

echo "Wait 10s before boost"
sleep 10

echo "# Boost subnet on the root subnet"
echo "1" | btcli root boost --netuid 1 --increase 1 --wallet.name validator --wallet.hotkey validator_hotkey --subtensor.chain_endpoint ws://subtensor_machine:9945 <<EOF
$COLDKEY_PASSWORD
y
EOF

# Attempt to register the validator and start it
if register_node validator; then
    echo "Validator registration successful. Starting the validator..."
    # Start the validator
    python /app/neurons/validator.py --netuid 1 --subtensor.chain_endpoint ws://subtensor_machine:9946 --wallet.name validator --wallet.hotkey validator_hotkey --axon.port 8092
else
    echo "Validator registration failed. Not starting the validator."
fi

# Keep the container running
tail -f /dev/null
