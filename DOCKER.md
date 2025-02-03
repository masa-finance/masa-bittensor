# Subnet 42 Masa Protocol Docker Image

Official Docker image for running subnet 42 Masa Protocol miners and validators.

## 🏷️ Tags

- `latest` - Latest stable release
- `sha-<commit>-<timestamp>` - Specific commit builds
- `v*.*.*` - Version releases

## 🔍 Quick Reference

- **Maintained by**: [MASA Finance](https://github.com/masa-finance)
- **Source**: [GitHub - masa-protocol](https://github.com/masa-finance/masa-bittensor)
- **Supported architectures**: `linux/amd64`, `linux/arm64`

## 📊 Supported Networks

- **TEST Network**
  - Subnet: 165
  - Uses test TAO
  - Perfect for learning and testing
  
- **MAIN Network** (Finney)
  - Subnet: 42
  - Uses real TAO
  - For production use only

## 🚀 Usage

### Basic Usage with Docker Compose

1. Clone and configure:
```bash
git clone https://github.com/masa-finance/masa-bittensor.git
cd masa-bittensor
cp .env.example .env
```

2. Configure your `.env` file with required settings:
```env
# Network settings
NETWORK=finney  # or 'test' for testnet
NETUID=42      # or '165' for testnet

# Masa Protocol settings (required)
TWITTER_API_KEY=your_key
TWITTER_API_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_SECRET=your_secret
TWITTER_BEARER_TOKEN=your_token

# Bittensor settings
COLDKEY_MNEMONIC=your_mnemonic
```

3. Start the services:
```bash
# Run a miner with required protocol node
docker-compose up -d
```

## 🔧 Configuration

### Environment Variables

#### Required
- `NETWORK`: Network to connect to (`test` or `finney`)
- `COLDKEY_MNEMONIC`: Your coldkey mnemonic
- Twitter API credentials for masa-protocol:
  - `TWITTER_API_KEY`
  - `TWITTER_API_SECRET`
  - `TWITTER_ACCESS_TOKEN`
  - `TWITTER_ACCESS_SECRET`
  - `TWITTER_BEARER_TOKEN`

#### Optional
- `WALLET_NAME`: Name of the wallet to use (default: `default`)
- `DEVICE`: Device to use (`cpu` or `cuda`)
- `LOGGING_DEBUG`: Logging level

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