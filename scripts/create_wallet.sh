#!/bin/bash

# Use environment variables for passwords
COLDKEY_PASSWORD=${COLDKEY_PASSWORD:-'default_coldkey_password'}
HOTKEY_PASSWORD=${HOTKEY_PASSWORD:-'default_hotkey_password'}

# Create a new coldkey with the specified password
echo -e "$COLDKEY_PASSWORD\n$COLDKEY_PASSWORD" | btcli wallet new_coldkey --wallet.name my_coldkey --wallet.password

# Create a new hotkey with the specified password
echo -e "$HOTKEY_PASSWORD\n$HOTKEY_PASSWORD" | btcli wallet new_hotkey --wallet.name my_coldkey --wallet.hotkey my_hotkey --wallet.password

# Use the faucet and automatically respond "y" to the prompt and provide the password
expect -c "
spawn btcli wallet faucet --wallet.name my_coldkey --subtensor.chain_endpoint ws://subnet_machine:9945 --wallet.password
expect \"Run Faucet ?\"
send \"y\r\"
expect \"Enter password to unlock key:\"
send \"$COLDKEY_PASSWORD\r\"
expect eof
"

echo "Wallet with coldkey and hotkey created, and faucet used successfully."
