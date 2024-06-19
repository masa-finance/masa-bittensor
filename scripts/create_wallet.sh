#!/bin/bash

# Use environment variables for passwords
COLDKEY_PASSWORD=${COLDKEY_PASSWORD:-'default_coldkey_password'}
HOTKEY_PASSWORD=${HOTKEY_PASSWORD:-'default_hotkey_password'}

# Function to run the faucet process and wait for it to complete
run_faucet() {
    WALLET_NAME=$1
    expect << EOF
set timeout 180
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


# Create and fund owner wallets
#
# Create a new coldkey with the specified password
echo -e "$COLDKEY_PASSWORD\n$COLDKEY_PASSWORD" | btcli wallet new_coldkey --wallet.name owner --wallet.password

# Create a new hotkey with the specified password
echo -e "$HOTKEY_PASSWORD\n$HOTKEY_PASSWORD" | btcli wallet new_hotkey --wallet.name owner --wallet.hotkey miner_hotkey --wallet.password

# Use the faucet for the owner wallet 3 times to get enough tTAO to register a subnet
run_faucet owner || { echo "Faucet 1 failed for owner wallet"; exit 1; }
run_faucet owner || { echo "Faucet 2 failed for owner wallet"; exit 1; }
run_faucet owner || { echo "Faucet 3 failed for owner wallet"; exit 1; }
run_faucet owner || { echo "Faucet 4 failed for owner wallet"; exit 1; }

echo -e "Owner faucet has run 4 times, now has 1200 τTAO"

# Register / Create a Subnet
echo -e "Registering a new subnet"

btcli subnet create --wallet.name owner --subtensor.chain_endpoint ws://127.0.0.1:9946 

# Create and fund miner wallets
#
# Create a new coldkey with the specified password
echo -e "$COLDKEY_PASSWORD\n$COLDKEY_PASSWORD" | btcli wallet new_coldkey --wallet.name miner --wallet.password

# Create a new hotkey with the specified password
echo -e "$HOTKEY_PASSWORD\n$HOTKEY_PASSWORD" | btcli wallet new_hotkey --wallet.name miner --wallet.hotkey miner_hotkey --wallet.password

# Use the faucet for the miner wallet
run_faucet miner || { echo "Faucet failed for miner wallet"; exit 1; }

# Create and fund validator wallets
#
# Create a new coldkey with the specified password
echo -e "$COLDKEY_PASSWORD\n$COLDKEY_PASSWORD" | btcli wallet new_coldkey --wallet.name validator --wallet.password

# Create a new hotkey with the specified password
echo -e "$HOTKEY_PASSWORD\n$HOTKEY_PASSWORD" | btcli wallet new_hotkey --wallet.name validator --wallet.hotkey validator_hotkey --wallet.password

# Use the faucet for the validator wallet
run_faucet validator || { echo "Faucet failed for validator wallet"; exit 1; }

echo "Wallets for miner and validator created, and faucet used successfully."
