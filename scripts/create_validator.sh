#!/bin/bash

# Use environment variables for passwords
COLDKEY_PASSWORD=${COLDKEY_PASSWORD:-'default_coldkey_password'}
HOTKEY_PASSWORD=${HOTKEY_PASSWORD:-'default_hotkey_password'}

# Import run_faucet()
source run_faucet.sh

# Create and fund validator wallets
#
# Create a new coldkey with the specified password
echo -e "$COLDKEY_PASSWORD\n$COLDKEY_PASSWORD" | btcli wallet new_coldkey --wallet.name validator --wallet.password

# Create a new hotkey with the specified password
echo -e "$HOTKEY_PASSWORD\n$HOTKEY_PASSWORD" | btcli wallet new_hotkey --wallet.name validator --wallet.hotkey validator_hotkey --wallet.password

# Use the faucet for the validator wallet
run_faucet validator || { echo "Faucet failed for validator wallet"; exit 1; }

echo "Wallets for validator created, and faucet used successfully."

# Expect script to handle the interactive prompts
expect << EOF
log_user 1
set timeout -1

# Loop until the correct netuid prompt is seen
while {1} {
    spawn btcli subnet register --wallet.name validator --wallet.hotkey validator_hotkey --subtensor.chain_endpoint ws://subtensor_machine:9946
    expect {
        "Enter netuid \\[0/3\\] (0):" {
            puts "Waiting for subnet creation..."
            sleep 5
            exp_continue
        }
        "Enter netuid \\[0/1/3\\] (0):" {
            puts "Correct netuid prompt received."
            send "1\r"
            exp_continue
        }
        "Do you want to continue? \\[y/n\\] (n)" {
            puts "Confirming continuation..."
            send "y\r"
            exp_continue
        }
        "Enter password to unlock key:" {
            puts "Entering password..."
            send "$COLDKEY_PASSWORD\r"
            exp_continue
        }
        "Recycle τ" {
            puts "Recycling τ..."
            send "y\r"
            exp_continue
        }
        "✅ Registered" {
            puts "Successfully registered."
            exit
        }
        eof {
            puts "Retrying registration..."
            sleep 1
        }
    }
}
EOF

tail -f /dev/null