#!/bin/bash
export LD_PRELOAD=/usr/local/lib/python3.10/site-packages/torch/lib/../../torch.libs/libgomp-4dbbc2f2.so.1.0.0
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

btcli wallet new_coldkey --wallet.name validator --no_password
btcli wallet new_hotkey --wallet.name validator --wallet.hotkey default --no_password

echo "y" | btcli wallet faucet --wallet.name validator --subtensor.chain_endpoint ws://54.205.45.3:9945 

echo -e "y\ny\ny" | btcli subnet register --wallet.name validator --wallet.hotkey default  --subtensor.chain_endpoint ws://54.205.45.3:9945 --netuid 1

python3 neurons/validator.py --wallet.name validator --wallet.hotkey default --logging.debug --netuid 1 --subtensor.chain_endpoint ws://54.205.45.3:9945