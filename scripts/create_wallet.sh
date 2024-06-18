#!/bin/bash

# Use environment variables for passwords
COLDKEY_PASSWORD=${COLDKEY_PASSWORD:-'default_coldkey_password'}
HOTKEY_PASSWORD=${HOTKEY_PASSWORD:-'default_hotkey_password'}

# Function to run the faucet process and wait for it to complete
run_faucet() {
    WALLET_NAME=$1
    expect << EOF
set timeout 120
log_user 1
spawn btcli wallet faucet --wallet.name $WALLET_NAME --subtensor.chain_endpoint ws://subnet_machine:9945 --wallet.password
expect {
    "Run Faucet ?" {
        send "y\r"
        exp_continue
    }
    "Enter password to unlock key:" {
        send "$COLDKEY_PASSWORD\r"
        exp_continue
    }
    "Balance:" {
        exp_continue
    }
    timeout {
        puts "Timeout waiting for faucet process to complete."
        exit 1
    }
    eof {
        exit
    }
}
EOF
}

# Create a new coldkey with the specified password
echo -e "$COLDKEY_PASSWORD\n$COLDKEY_PASSWORD" | btcli wallet new_coldkey --wallet.name miner_coldkey --wallet.password

# Create a new hotkey with the specified password
echo -e "$HOTKEY_PASSWORD\n$HOTKEY_PASSWORD" | btcli wallet new_hotkey --wallet.name miner_coldkey --wallet.hotkey miner_hotkey --wallet.password

# Use the faucet for the miner wallet
run_faucet miner_coldkey || { echo "Faucet failed for miner wallet"; exit 1; }

# Create a new coldkey with the specified password
echo -e "$COLDKEY_PASSWORD\n$COLDKEY_PASSWORD" | btcli wallet new_coldkey --wallet.name validator_coldkey --wallet.password

# Create a new hotkey with the specified password
echo -e "$HOTKEY_PASSWORD\n$HOTKEY_PASSWORD" | btcli wallet new_hotkey --wallet.name validator_coldkey --wallet.hotkey validator_hotkey --wallet.password

# Use the faucet for the validator wallet
run_faucet validator_coldkey || { echo "Faucet failed for validator wallet"; exit 1; }

echo "Wallets for miner and validator created, and faucet used successfully."
