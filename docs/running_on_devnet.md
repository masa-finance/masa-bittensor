# Development Setup

This guide assumes that you have Bittensor and a virtual environment (venv/conda) with the `apple_m1_environment.yml` already installed.

## Wallet Setup

First, create three cold wallets: `owner`, `miner`, and `validator`. For `miner` and `validator`, create a hot wallet (`default`). Use the following commands:

bash
btcli wallet new_coldkey --wallet.name <name>
btcli wallet new_hotkey --wallet.name <name of the cold wallet> --wallet.hotkey default



## Mint Tokens

Next, mint tokens for these wallets:

bash
btcli wallet faucet --wallet.name <name of the wallet> --subtensor.chain_endpoint ws://54.157.190.36:9945



**Note:** If you are creating a new subnet, you need at least 1000 tTAO in the `owner` wallet. Otherwise, just fund `miner` and `validator`.

## Create Subnet

To create a subnet, use:

btcli subnet create --wallet.name owner --subtensor.chain_endpoint ws://54.157.190.36:9945


## Register Wallets to Subnet

Register your `validator` and `miner` to the subnet:

btcli subnet register --wallet.name <wallet name> --wallet.hotkey default --subtensor.chain_endpoint ws://54.157.190.36:9945 --netuid 1



**Note:** You may encounter an error about exceeding blocks. This is normal; wait for one tempo (approximately 1 hour).

## Stake on Validator

Stake on the `validator` to set your weights:

btcli stake add --wallet.name validator --wallet.hotkey default --subtensor.chain_endpoint ws://54.157.190.36:9945 --netuid 1



## Register Validator on Root Subnet

Register your `validator` on the root subnet:

btcli root register --wallet.name validator --wallet.hotkey --subtensor.chain_endpoint ws://54.157.190.36:9945 --netuid 1



Then, set your weights:

btcli root boost --netuid 1 --increase 1 --wallet.name validator --wallet.hotkey default --subtensor.chain_endpoint ws://54.157.190.36:9945

**Note:** You may encounter an error like 'setting weights too fast', which also means wait for another hour.

## Run Miner and/or Validator

Finally, run the `miner` and/or `validator`:

python neurons/miner.py --netuid 1  --wallet.name miner --wallet.hotkey default --logging.debug --subtensor.chain_endpoint ws://54.157.190.36:9945 

or 

python neurons/validator.py --netuid 1 --wallet.name validator --wallet.hotkey default --logging.debug --subtensor.chain_endpoint ws://54.157.190.36:9945




**Important:** Don't forget to add the flags `--subtensor.chain_endpoint ws://54.157.190.36:9945` and `--netuid 1` to each command. These flags point to our devnet and specify the subnet ID, respectively.