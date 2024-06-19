#!/bin/bash

# Use environment variables for passwords
COLDKEY_PASSWORD=${COLDKEY_PASSWORD:-'default_coldkey_password'}
HOTKEY_PASSWORD=${HOTKEY_PASSWORD:-'default_hotkey_password'}

# Import run_faucet()
source ./run_faucet.sh

# Create and fund validator wallets
#
# Create a new coldkey with the specified password
echo -e "$COLDKEY_PASSWORD\n$COLDKEY_PASSWORD" | btcli wallet new_coldkey --wallet.name validator --wallet.password

# Create a new hotkey with the specified password
echo -e "$HOTKEY_PASSWORD\n$HOTKEY_PASSWORD" | btcli wallet new_hotkey --wallet.name validator --wallet.hotkey validator_hotkey --wallet.password

# Use the faucet for the validator wallet
run_faucet validator || { echo "Faucet failed for validator wallet"; exit 1; }

echo "Wallets for miner and validator created, and faucet used successfully."
