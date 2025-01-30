# MASA Bittensor Mining Stack

Run MASA Bittensor miners and validators easily using Docker Swarm. Scale from 1 to 255 miners with a simple configuration!

## 🚀 Quick Start

1. Clone this repository:
```bash
git clone https://github.com/masaengineering/masa-bittensor.git
cd masa-bittensor
```

2. Create your `.env` file:
```bash
cp .env.sample .env
```

3. Configure your `.env` file with your coldkey mnemonic and desired number of miners/validators:
```env
MINER_COUNT=1          # Number of miners to run (1-255)
VALIDATOR_COUNT=1      # Number of validators to run (0-255)
COLDKEY_MNEMONIC=""    # Your coldkey mnemonic phrase
NETWORK=finney        # Network to connect to (finney/test)
LOGGING_DEBUG=INFO    # Logging level (DEBUG/INFO/WARNING/ERROR)
```

4. Initialize Docker Swarm (if not already initialized):
```bash
docker swarm init
```

5. Deploy the stack:
```bash
# Pull latest published image and deploy
docker stack deploy -c docker-compose.yml masa

# OR build locally first if needed
docker compose build
DOCKER_IMAGE=masa-bittensor:latest docker stack deploy -c docker-compose.yml masa
```

That's it! Your miners and validators will start automatically.

## 📦 Image Handling

The stack is configured to handle images in this order:

1. If `DOCKER_IMAGE` is set in your `.env`, it will use that specific image
2. Otherwise, it will try to pull `masaengineering/masa-bittensor:latest` from Docker Hub
3. If the pull fails, it will automatically build the image locally

This means you can:
- Use the latest published image by default (fastest)
- Override with a specific version using `DOCKER_IMAGE=masaengineering/masa-bittensor:1.2.3`
- Build locally when needed using `docker compose build`

## 📊 Monitoring Your Nodes

### View Service Status
```bash
docker service ls
```

### Check Logs
View all logs:
```bash
docker service logs masa_miner
docker service logs masa_validator
```

Follow logs in real-time:
```bash
docker service logs -f masa_miner
docker service logs -f masa_validator
```

### View Individual Miner/Validator Logs
For a specific miner instance (replace N with instance number 1-255):
```bash
docker service logs "masa_miner.N"
```

## 🔧 Configuration

### Scaling
You can run up to 255 miners and validators. Simply adjust the `MINER_COUNT` and `VALIDATOR_COUNT` in your `.env` file.

Example for running 10 miners:
```env
MINER_COUNT=10
VALIDATOR_COUNT=1
```

### Port Ranges
- Miners: 8155-8165 (API), 9164-9174 (Metrics)
- Validators: 8091-8100 (API), 9100-9109 (Metrics)

### Storage
The stack uses these volume mounts:
- `~/.bittensor/wallets`: Wallet storage
- `~/.bt-masa`: Logging directory
- Local directories for code and configuration

## 🛠 Advanced Usage

### Building Locally
To build and use a local image instead of pulling from Docker Hub:
```bash
docker compose build
DOCKER_IMAGE=masa-bittensor:latest docker stack deploy -c docker-compose.yml masa
```

### Using Specific Versions
To use a specific version from Docker Hub:
```bash
DOCKER_IMAGE=masaengineering/masa-bittensor:specific-tag docker stack deploy -c docker-compose.yml masa
```

## 📝 Common Operations

### Stop All Services
```bash
docker stack rm masa
```

### Update Services
```bash
docker stack deploy -c docker-compose.yml masa
```

### View Running Containers
```bash
docker ps
```

## 🤝 Support

For support, please join our [Discord](https://discord.gg/masa) or open an issue on GitHub.

## ⚠️ Important Notes

1. Ensure your coldkey mnemonic is kept secure and never share it
2. Back up your wallet files regularly
3. Monitor your nodes' performance and logs
4. Ensure you have sufficient system resources when running multiple miners

## 🔐 Security

Store your coldkey mnemonic securely. Never commit your `.env` file to version control.
