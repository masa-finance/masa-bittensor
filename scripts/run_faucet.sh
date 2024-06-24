#!/bin/bash

# Use environment variables for passwords
COLDKEY_PASSWORD=${COLDKEY_PASSWORD:-'default_coldkey_password'}
HOTKEY_PASSWORD=${HOTKEY_PASSWORD:-'default_hotkey_password'}

# Function to run the faucet process and wait for it to complete
run_faucet() {
    WALLET_NAME=$1
    expect << EOF
set timeout 360
log_user 1
spawn btcli wallet faucet --wallet.name $WALLET_NAME --subtensor.chain_endpoint ws://subtensor_machine:9945 --wallet.password
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
