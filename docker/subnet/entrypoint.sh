#!/bin/bash

# Import shared functions
source /app/functions.sh

# Create and fund owner wallets
#
# Create a new coldkey with the specified password
echo -e "$COLDKEY_PASSWORD\n$COLDKEY_PASSWORD" | btcli wallet new_coldkey --wallet.name owner --wallet.password

# Create a new hotkey with the specified password
echo -e "$HOTKEY_PASSWORD\n$HOTKEY_PASSWORD" | btcli wallet new_hotkey --wallet.name owner --wallet.hotkey owner_hotkey --wallet.password

# Run upgraded faucet once (gives 1000TAO)
run_faucet owner || { echo "Faucet failed for owner wallet"; exit 1; }

# Wait for all background processes to finish
wait

# Check if any of the faucet operations failed
for job in $(jobs -p); do
    wait $job || { echo "A faucet operation failed"; exit 1; }
done

echo -e "faucet to owner wallet has run, now has 3000 τTAO"

# Register / Create a Subnet using expect to handle the interactive prompt and password
expect << EOF
log_user 1
spawn btcli subnet create --wallet.name owner --subtensor.chain_endpoint ws://subtensor_machine:9945
expect {
    "Do you want to register a subnet for" {
        send "y\r"
        exp_continue
    }
    "Enter password to unlock key:" {
        send "$COLDKEY_PASSWORD\r"
        exp_continue
    }
    eof
}
EOF
sleep 10
btcli subnet list --subtensor.chain_endpoint ws://subtensor_machine:9945

echo "Wait 10s before setting hyperparam"
sleep 10

echo "Set hyperparam to allow setting weights now"
echo "1" | btcli sudo set --param weights_rate_limit --value 1 --subtensor.chain_endpoint ws://subtensor_machine:9945 --wallet.name owner --netuid 1 <<EOF
$COLDKEY_PASSWORD
y
EOF

tail -f /dev/null
