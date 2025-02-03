# MASA Bittensor Node Image

Official Docker image for running MASA Bittensor miners and validators.

## 🏷️ Tags

- `latest` - Latest stable release
- `sha-<commit>-<timestamp>` - Specific commit builds
- `v*.*.*` - Version releases

## 🔍 Quick Reference

- **Maintained by**: [MASA Finance](https://github.com/masa-finance)
- **Source**: [GitHub - masa-bittensor](https://github.com/masa-finance/masa-bittensor)
- **Supported architectures**: `linux/amd64`, `linux/arm64`

## 📊 Supported Networks

- **TEST Network** (Default)
  - Subnet: 165
  - Uses test TAO
  - Perfect for learning and testing
  
- **MAIN Network** (Finney)
  - Subnet: 42
  - Uses real TAO
  - For production use only

## 🚀 Usage

### Basic Usage with Docker Compose

```yaml
services:
  miner:
    image: masaengineering/masa-bittensor:latest
    environment:
      - NETWORK=test
      - WALLET_NAME=default
      - ROLE=miner
    volumes:
      - ~/.bittensor/wallets:/root/.bittensor/wallets
      - ~/.bt-masa:/root/.bt-masa
```

### Docker Swarm Deployment

For production use, we recommend using our Docker Swarm setup:
1. Clone the repository
2. Configure your `.env`
3. Run `./start.sh`

See our [GitHub Repository](https://github.com/masa-finance/masa-bittensor) for full documentation.

## 🔧 Configuration

### Environment Variables

- `NETWORK`: Network to connect to (`test` or `finney`)
- `WALLET_NAME`: Name of the wallet to use (default: `default`)
- `ROLE`: Node role (`miner` or `validator`)
- `DEVICE`: Device to use (`cpu` or `cuda`)
- `LOGGING_DEBUG`: Logging level
- `COLDKEY_MNEMONIC`: Your coldkey mnemonic (required)

### Volumes

- `/root/.bittensor/wallets`: Wallet storage
- `/root/.bt-masa`: Logging directory

## 🏗️ Building Locally

```bash
git clone https://github.com/masa-finance/masa-bittensor.git
cd masa-bittensor
docker compose build
```

## 📝 License

MIT License - see [LICENSE](https://github.com/masa-finance/masa-bittensor/blob/main/LICENSE) for details.

## 🤝 Support

- [GitHub Issues](https://github.com/masa-finance/masa-bittensor/issues)
- [Discord Community](https://discord.gg/masa) 