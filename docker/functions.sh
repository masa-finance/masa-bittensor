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

# Function to check if subnet 1 exists
check_subnet_exists() {
    local output
    output=$(btcli subnet list --subtensor.chain_endpoint ws://subtensor_machine:9945)
    echo "Current subnet list:"
    echo "$output"
    echo "$output" | awk 'NR>1 {print $1, $2}' | grep -q "^ *1 "
}

# Function to register a miner or validator
register_node() {
    local node_type=$1
    local wallet_name="${node_type}"
    local hotkey_name="${node_type}_hotkey"
    local attempt=1
    local max_attempts=5

    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt to register ${node_type}..."

        output=$(btcli subnet register --wallet.name $wallet_name --wallet.hotkey $hotkey_name --subtensor.chain_endpoint ws://subtensor_machine:9946 2>&1)

        if echo "$output" | grep -q "Enter netuid \[0/1/3\] (0):"; then
            echo "1" | btcli subnet register --wallet.name $wallet_name --wallet.hotkey $hotkey_name --subtensor.chain_endpoint ws://subtensor_machine:9946 <<EOF
1
y
$COLDKEY_PASSWORD
y
EOF
            if [ $? -eq 0 ]; then
                echo "Successfully registered ${node_type}."
                return 0
            fi
        fi
        echo "Registration attempt failed. Waiting 15 seconds before retrying..."
        sleep 15
        ((attempt++))
    done
    echo "Failed to register ${node_type} after $max_attempts attempts."
    return 1
}
