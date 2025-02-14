# Masa Bittensor Subnet

Welcome to the Masa Bittensor Subnet! Follow our [documentation](https://developers.masa.ai/docs/masa-subnet/welcome) to get started as a miner or validator. We are subnet #42 on mainnet and #165 on testnet.

## About Masa's Subnets

### 🌐 Subnet 42: The Real-Time Data-Scraping Powerhouse
Join the data revolution with Subnet 42, where:
- Miners extract trending tweets from X (Twitter) in real-time
- Validators ensure data quality, freshness, and relevance
- High-quality, real-time data powers Subnet 59's AI agents
- Minimal latency and maximum reliability

**What Makes Subnet 42 Special:**
- **Real-time Data**: Provides high-quality, real-time data for AI development
- **Powers Innovation**: Drives AI development through reliable data streams
- **Fair Rewards**: Uses sophisticated kurtosis reward curve for fair compensation
- **Quality Assurance**: Distributed validation network ensures data reliability
- **Low Latency**: Optimized for real-time data processing and delivery

**How It Works:**
1. Miners use the Masa SDK to extract trending tweets
2. Validators ensure relevance, quality, and accuracy
3. Contributors are rewarded based on performance
4. Data flows to Subnet 59 to power AI agent interactions

This repository contains everything you need to participate in Subnet 42 as either a miner or validator.

### 🎮 Subnet 59: The Agent Arena
Want to participate in both subnets? Check out [The Agent Arena (Subnet 59)](https://github.com/masa-finance/agent-arena-subnet) where:
- AI agents compete and evolve in a Darwinian playground
- Performance is measured through genuine user engagement
- Agents are powered by real-time data from Subnet 42
- Success is measured by real-world impact and user interaction

**Key Features:**
- Deploy AI agents that interact on X (Twitter)
- Earn rewards based on genuine engagement metrics
- Access real-time data through Subnet 42
- Access AI Inference through partner networks
- Launch AI Agent Memecoins to boost performance
- Compete in the first evolutionary arena for AI agents

By participating in both subnets, you can:
1. Earn rewards from data scraping (Subnet 42)
2. Power AI agent interactions (Subnet 59)
3. Maximize your earning potential across both networks
4. Contribute to both data collection and AI advancement
5. Be part of the first truly competitive AI agent ecosystem

Ready to get started? Follow the setup instructions below!

## Server Setup

### Option A: Local Setup
First, ensure you have Python 3.12 and Node.js installed on your system.

### Option B: Digital Ocean Setup
1. Create a Digital Ocean account and navigate to **Droplets**
2. Click "Create Droplet" (default configuration is fine)
3. Set up SSH authentication:
   ```bash
   # Generate SSH key if you don't have one
   ssh-keygen -t rsa -b 4096
   
   # Add your key to Digital Ocean during droplet creation
   ```
4. After creating the droplet, connect via SSH:
   ```bash
   ssh -i ~/.ssh/id_rsa root@<droplet-ip-address>
   ```
5. Install system dependencies:
   ```bash
   # Add Python 3.12 repository
   sudo add-apt-repository ppa:deadsnakes/ppa
   sudo apt update
   
   # Install Python, Node.js, and npm
   sudo apt install python3.12 python3.12-venv nodejs npm
   
   # Create and activate virtual environment
   python3.12 -m venv venv
   source venv/bin/activate
   ```

## Common Setup

1. Install PM2 (Process Manager):
   ```bash
   sudo npm install pm2 -g
   ```

2. Clone and set up the repository:
   ```bash
   git clone https://github.com/masa-finance/masa-bittensor.git
   cd masa-bittensor
   python -m pip install -e .
   ```

## Wallet Setup

Before running a validator or miner, you need to create and register your wallet.

### 1. Create Your Wallet

#### For Validators

1. Create a cold wallet:
   ```bash
   btcli wallet new --wallet.name validator
   ```

2. Create a hot wallet (using the same name):
   ```bash
   btcli wallet new --wallet.name validator --wallet.hotkey default
   ```

3. Verify your wallets:
   ```bash
   btcli wallet list
   ```
   You should see your `validator` wallet listed with its associated hotkey (`default`).

#### For Miners

1. Create a cold wallet:
   ```bash
   btcli wallet new --wallet.name miner
   ```

2. Create a hot wallet (using the same name):
   ```bash
   btcli wallet new --wallet.name miner --wallet.hotkey default
   ```

3. Verify your wallets:
   ```bash
   btcli wallet list
   ```
   You should see your `miner` wallet listed with its associated hotkey (`default`).

### 2. Fund Your Wallet

You'll need TAO tokens to register on the network. The amount needed varies based on network conditions.

#### For Testnet (Subnet 165)
1. Join [Bittensor's Discord](https://discord.gg/bittensor)
2. Navigate to the Testnet channel
3. Request tTAO by providing your coldkey address
4. Check your balance:
   ```bash
   btcli wallet balance --wallet.name <miner|validator> --subtensor.network test
   ```

#### For Mainnet (Subnet 42)
1. Purchase TAO from supported exchanges:
   - [CoinMarketCap Markets](https://coinmarketcap.com/currencies/bittensor/markets/)
   - [ChangeNow.io](https://changenow.io)
2. Send TAO to your coldkey address
3. Check your balance:
   ```bash
   btcli wallet balance --wallet.name <miner|validator>
   ```

💡 **Tips for Registration**:
- Monitor current registration costs: `btcli subnets list`
- Registration uses Proof of Work (PoW), so costs vary with network activity
- Always keep extra TAO for transaction fees
- Check registration status: `btcli subnets list --subtensor.network <finney|test>`

### 3. Register Your Wallet

#### For Validators
```bash
# For mainnet (subnet 42)
btcli subnet register --wallet.name validator --wallet.hotkey default --netuid 42

# For testnet (subnet 165)
btcli subnet register --wallet.name validator --wallet.hotkey default --netuid 165 --subtensor.network test
```

#### For Miners
```bash
# For mainnet (subnet 42)
btcli subnet register --wallet.name miner --wallet.hotkey default --netuid 42

# For testnet (subnet 165)
btcli subnet register --wallet.name miner --wallet.hotkey default --netuid 165 --subtensor.network test
```

⚠️ **Important**: 
- Keep your wallet passwords safe! You'll need them for future operations.
- Your wallet files will be stored in `~/.bittensor/wallets/`
- Registration may take multiple attempts due to POW requirements
- Back up your keys after successful registration

## Register Your Neuron on Masa Subnet

After creating and funding your wallet, you need to register your neuron on the Masa subnet.

### Check Registration Status
```bash
# View all subnets and their registration requirements
btcli subnets list

# Check specific details for Masa subnet
btcli subnets list | grep "42"
```

### Register on Mainnet (Subnet 42)

1. For Validators:
   ```bash
   # Register on Masa subnet
   btcli subnet register --wallet.name validator --wallet.hotkey default --netuid 42
   
   # Verify registration
   btcli subnet list --wallet.name validator --netuid 42
   ```

2. For Miners:
   ```bash
   # Register on Masa subnet
   btcli subnet register --wallet.name miner --wallet.hotkey default --netuid 42
   
   # Verify registration
   btcli subnet list --wallet.name miner --netuid 42
   ```

💡 **Registration Tips**:
- Registration uses Proof of Work (PoW) and may take several attempts
- Cost varies based on network activity
- Keep your terminal open during registration
- If registration fails, try again - this is normal
- Monitor your registration status with `btcli wallet overview`

### Optional: Register on Testnet First
If you want to test your setup first:
```bash
# For validators
btcli subnet register --wallet.name validator --wallet.hotkey default --netuid 165 --subtensor.network test

# For miners
btcli subnet register --wallet.name miner --wallet.hotkey default --netuid 165 --subtensor.network test
```

## Validator Setup

1. Ensure your validator wallet is in the correct location:
   ```bash
   ~/.bittensor/wallets/validator/default/
   ```

2. Start the Validator:
   ```bash
   # For mainnet (subnet 42)
   pm2 start "make run-validator" --name "masa-validator"
   
   # For testnet (subnet 165)
   pm2 start "make run-validator NETWORK=test" --name "masa-validator-test"
   ```

3. Monitor your validator:
   ```bash
   # View logs
   pm2 logs masa-validator
   
   # Check status
   pm2 status
   
   # Save PM2 process list
   pm2 save
   
   # Enable startup script
   pm2 startup
   ```

## Miner Setup

1. Ensure your miner wallet is in the correct location:
   ```bash
   ~/.bittensor/wallets/miner/default/
   ```

2. Start the Miner:
   ```bash
   # For mainnet (subnet 42)
   pm2 start "make run-miner" --name "masa-miner"
   
   # For testnet (subnet 165)
   pm2 start "make run-miner NETWORK=test" --name "masa-miner-test"
   ```

3. Monitor your miner:
   ```bash
   # View logs
   pm2 logs masa-miner
   
   # Check status
   pm2 status
   
   # Save PM2 process list
   pm2 save
   
   # Enable startup script
   pm2 startup
   ```

## PM2 Management Commands

Common commands for managing your nodes:
```bash
# View all processes
pm2 status

# Stop processes
pm2 stop masa-validator
pm2 stop masa-miner

# Restart processes
pm2 restart masa-validator
pm2 restart masa-miner

# Remove processes
pm2 delete masa-validator
pm2 delete masa-miner
pm2 delete all

# Save current process list
pm2 save

# Generate startup script
pm2 startup
```

## Monitor Network Performance

### 📊 TaoStats Explorer

[TaoStats.io](https://taostats.io) is the official block explorer and analytics platform for the Bittensor network. Use it to:

1. **Monitor Subnet Performance**:
   - [Subnet 42 Stats](https://taostats.io/subnets/42) - Track Masa's Data Scraping subnet
   - [Subnet 59 Stats](https://taostats.io/subnets/59) - Monitor the Agent Arena subnet

2. **Track Your Performance**:
   - View your validator/miner rankings
   - Monitor your rewards and emissions
   - Track delegation and staking metrics
   - Analyze network-wide performance

3. **Network Analytics**:
   - Real-time blockchain data
   - Subnet-specific metrics
   - Validator and miner statistics
   - Delegation and staking information
   - Transaction history

4. **Key Metrics**:
   - Registration costs
   - Network activity
   - Stake distributions
   - Reward distributions
   - Historical performance data

💡 **Pro Tip**: Bookmark your validator/miner's address on TaoStats for quick access to performance metrics and network statistics.

## Contributing

For development workflows and contribution guidelines, please see `CONTRIBUTING.md`.

## dTAO Alpha: 15M MASA Reward Program

Earn a share of **15-million MASA tokens** (valued at $700,000 at $0.047 per token) through our Alpha Token Holding program.

### Program Requirements

1. **Stake MASA Tokens**:
   - Minimum requirement: **1,500 MASA**
   - APY range: 15%-25%
   - Staking periods: 3, 6, or 9 months
   - Supported networks: Ethereum, Base, BNB Chain

2. **Stake Masa Subnet Alpha Tokens**:
   - Earn Alpha Tokens by:
     - Mining or validating on Subnets 42/59
     - Staking TAO to these subnets

### How to Participate

1. **Stake TAO to Subnet**:
   ```bash
   # Stake specific amount
   btcli stake add --amount 10 --netuid 42

   # Stake all available TAO
   btcli stake add --all --netuid 42

   # Safe staking with 5% slippage protection
   btcli stake add --amount 10 --netuid 42 --safe --tolerance 0.05
   ```

2. **Delegate Alpha Tokens**:
   
   Stake to our official validators:
   
   **Subnet 42**:
   ```bash
   # Validator UID: 29
   btcli delegate add --amount 50 --hotkey 5ChhHEqBdPm5St9kwndwdP8Y1bXWZc14XabDUJLtgGFiZuHV --netuid 42
   ```

   **Subnet 59**:
   ```bash
   # Validator UID: 10
   btcli delegate add --amount 50 --hotkey 5CZv4oXgYsAFjJj8rLmmbLG29y7x9RGEc6hM9tzCwRU8NeDe --netuid 59
   ```

### Holding Requirements

- Maintain alpha token emissions for **120 days** minimum
- Keep **100%** of alpha tokens staked
- No sales allowed during the period
- Keep tokens in original hotkey (no transfers)

### Reward Structure

1. **Base Weight**: Determined by alpha token holdings
2. **MASA Token Stake**: Additional weight from MASA tokens
3. **Duration Bonuses**:
   - 6-month stake: 20% APY
   - 9-month stake: 25% APY
4. **Early Bird Bonus**: Special multiplier for early participants

### Distribution Details

- Rewards distributed after 120-day holding period
- Linear unlock over 3 months
- All distributions verifiable on-chain
- Transparent calculation system

### Manage Your Delegations

```bash
# View current delegations
btcli delegate list

# Remove delegation
btcli delegate remove --amount <AMOUNT> --hotkey <VALIDATOR_HOTKEY> --netuid <SUBNET_ID>

# Remove all delegation
btcli delegate remove --all --hotkey <VALIDATOR_HOTKEY> --netuid <SUBNET_ID>
```

For more information about the program, visit our [documentation](https://developers.masa.ai/docs/masa-subnet/d-tao-rewards).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
