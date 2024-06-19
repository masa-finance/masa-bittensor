#!/bin/bash

# Use environment variables for passwords
COLDKEY_PASSWORD=${COLDKEY_PASSWORD:-'default_coldkey_password'}
HOTKEY_PASSWORD=${HOTKEY_PASSWORD:-'default_hotkey_password'}

# Import the run_faucet function
source run_faucet.sh

# Create and fund miner wallets
#
# Create a new coldkey with the specified password
echo -e "$COLDKEY_PASSWORD\n$COLDKEY_PASSWORD" | btcli wallet new_coldkey --wallet.name miner --wallet.password

# Create a new hotkey with the specified password
echo -e "$HOTKEY_PASSWORD\n$HOTKEY_PASSWORD" | btcli wallet new_hotkey --wallet.name miner --wallet.hotkey miner_hotkey --wallet.password

# Use the faucet for the miner wallet
run_faucet miner || { echo "Faucet failed for miner wallet"; exit 1; }
