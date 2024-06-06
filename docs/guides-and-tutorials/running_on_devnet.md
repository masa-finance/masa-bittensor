---
id: devnet-guide
title: Devnet Guide
---

This guide provides a comprehensive walkthrough for setting up a local miner and validator on the Masa Devnet.

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

### 4. Set Python Path

```bash
export PYTHONPATH=$PYTHONPATH:<path_to_this_repo>
```

### 5. Verify Subtensor Environment

In the `Makefile`, ensure `SUBTENSOR_ENVIRONMENT` is set to `DEVNET`. If you are interested in running subtensor locally, set `SUBTENSOR_ENVIRONMENT` to `LOCAL`, and verify `LOCAL_ENDPOINT` is set correctly.

## Wallet Setup

### 6. Create cold wallets

Create cold wallets for a `miner` and `validator`.

```bash
btcli wallet new_coldkey --wallet.name miner
btcli wallet new_coldkey --wallet.name validator
```

### 7. Create hot wallets

Create hot wallets (`default`) for each cold wallet

```bash
btcli wallet new_hotkey --wallet.name miner --wallet.hotkey default
btcli wallet new_hotkey --wallet.name validator --wallet.hotkey default
```

### 8. Verify creation of wallets

```bash
make list-wallets
```

You should see two wallets listed, each with an associated hotkey (`default`)

### 9. Mint Tokens

Next, mint tokens for these wallets.

```bash
make fund-miner-wallet
make fund-validator-wallet
```

### 10. Register Wallets to Subnet

Register your `miner` and `validator` to the subnet `1`:

```bash
make register-validator
make register-miner
```

**Note:** You may encounter an error about exceeding blocks. This is normal; wait for one tempo (approximately 1 hour).

### 11. Stake on Validator

Stake TAO on the `validator` hotkey to finish registration:

```bash
make stake-validator
```

### 12. Register Validator on Root Subnet

Register your `validator` on the root subnet:

```bash
make register-validator-root
```

### 13. Set Weights

Then, set your weights:

```bash
make boost-root
```

**Note:** You may encounter an error like 'setting weights too fast', which also means wait for another hour.

## Run Masa Protocol

### 14. Run Miner and Validator

Finally, in two seperate terminals, run the `miner` and `validator`:

```bash
make run-miner
```

and

```bash
make run-validator
```

### 15. Interact with Validator API

Head to `http://localhost:8000/docs` to interact with the Validator API.

**Important:** If using the `btcli` directly and not `make` commands, remember to add the flags `--subtensor.chain_endpoint ws://54.205.45.3:9945` and `--netuid 1` to each command. These flags point to our devnet and specify the subnet ID, respectively.
