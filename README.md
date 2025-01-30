# Masa Bittensor Docker Setup

Run Masa Bittensor nodes with a simple Docker-based setup.

## Quick Start

1. Initialize Docker Swarm:
   ```bash
   docker swarm init
   ```

2. Configure your settings:
   - Copy `.env.example` to `.env`
   - Edit `.env` file:
     ```
     # Required: Your Wallet's Coldkey Mnemonic
     COLDKEY_MNEMONIC="your twelve word mnemonic phrase here"
     
     # How Many Nodes to Run (defaults: 0 validators, 1 miner)
     VALIDATOR_COUNT=0
     MINER_COUNT=1
     
     # Network (use 'finney' for mainnet)
     NETWORK=test
     ```

3. Start everything:
   ```bash
   docker stack deploy -c docker-compose.yml masa
   ```

You'll see a startup report showing:
- Registration status for each node
- UIDs on the network
- Running status
- Port assignments
- Hotkey addresses

4. Stop everything:
   ```bash
   docker stack rm masa
   ```

## Wallet Setup

Your wallet will be automatically:
- Created if using a mnemonic in `.env`
- Used if existing in `~/.bittensor/wallets`

## Troubleshooting

View detailed logs:
```bash
# Find container IDs
docker ps | grep masa

# View logs from specific container
docker logs -f CONTAINER_ID
```

Common Issues:
- Port conflicts: Ensure ports are available
- Service not starting: Check container logs
- Registration failed: Verify your mnemonic and network settings

## Support

- Issues: [GitHub Issues](https://github.com/masa-finance/masa-bittensor/issues)
- Discord: [Masa Finance](https://discord.gg/masafinance) 