## Environment Setup

### 1. Create virtual environment

If you do not already have a dedicated virtual envionment for Bittensor, you can create one using conda:

```bash
conda create --name bittensor python
```

### 2. Activate virtual environment

Please remember to always activate the environment when opening a new terminal!

```bash
conda activate bittensor
```

### 3. Install packages

In the root of this repository, run:

```bash
pip install -r requirements.txt
```

### 4. Finish setup

```bash
export PYTHONPATH=$PYTHONPATH:<path_to_this_repo>
```

For more details on how to install Bittensor and set up the virtual environment, please refer to the [official Bittensor installation guide](https://github.com/opentensor/bittensor#install).

## Wallet Setup

### 1. Create cold wallets

Create wallets for an `owner`, `miner`, and `validator`.

```bash
btcli wallet new_coldkey --wallet.name <name>
```

### 2. Create hot wallets

For `miner` and `validator`, also create a hot wallet (`default`).

```bash
btcli wallet new_hotkey --wallet.name <name> --wallet.hotkey default
```

### 3. Verify creation of wallets

```bash
make list-wallets
```

You should see your three wallets listed, with `miner` and `validator` also having a hotkey (`default`) assigned to them.

### 4. Mint Tokens

Next, mint tokens for these wallets. **Note:** If you are creating a new subnet, you need at least 1000 tTAO in the `owner` wallet. Otherwise, just fund `miner` and `validator` once.

```bash
make fund-miner-wallet
make fund-validator-wallet

# if creating a subnet
make fund-owner-wallet
```

## Create Subnet

To create a subnet, use the following command. **Note:** there is no need to create a new subnet in this walkthrough.

```bash
make create-subnet
```

## Register Wallets to Subnet

Register your `validator` and `miner` to the subnet:

```bash
make register-validator
make register-miner
```

**Note:** You may encounter an error about exceeding blocks. This is normal; wait for one tempo (approximately 1 hour).

## Stake on Validator

Stake TAO on the `validator` hotkey to enable the ability to set weights:

```bash
make stake-validator
```

## Register Validator on Root Subnet

Register your `validator` on the root subnet:

```bash
make register-validator-root
```

Then, set your weights:

```bash
make boost-root
```

**Note:** You may encounter an error like 'setting weights too fast', which also means wait for another hour.

## Run Miner and/or Validator

Finally, run the `miner` and/or `validator`:

```bash
make run-miner
```

or

```bash
make run-validator
```

**Important:** If using the `btcli` directly and not `make` commands, remember to add the flags `--subtensor.chain_endpoint ws://54.205.45.3:9945` and `--netuid 1` to each command. These flags point to our devnet and specify the subnet ID, respectively.
