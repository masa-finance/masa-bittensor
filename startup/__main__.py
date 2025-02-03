"""Main Startup Module for Agent Arena Subnet.

This module serves as the entry point for both validator and miner services.
It handles:
- Environment configuration
- Wallet setup and registration
- Process execution
- Status reporting

The module determines the role (validator/miner) from environment variables
and starts the appropriate service with proper configuration.

Environment Variables:
    ROLE: Service role ("validator" or "miner")
    SUBTENSOR_NETWORK: Network to connect to ("test" or "finney")
    NETUID: Network UID (249 for testnet, 59 for mainnet)
    VALIDATOR_AXON_PORT: Validator's axon port
    VALIDATOR_METRICS_PORT: Validator's Prometheus port
    VALIDATOR_GRAFANA_PORT: Validator's Grafana port
    MINER_AXON_PORT: Miner's axon port
    MINER_METRICS_PORT: Miner's Prometheus port
    MINER_GRAFANA_PORT: Miner's Grafana port
    REPLICA_NUM: Instance number for multiple replicas
"""

import os
import logging
from startup import WalletManager, ProcessManager
import bittensor as bt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def print_status_report(
    role: str,
    uid: int,
    hotkey: str,
    registered: bool,
    network: str,
    netuid: int,
    axon_port: int,
    metrics_port: int,
    grafana_port: int,
) -> None:
    """Print a formatted status report for the service.

    Displays a nicely formatted report showing:
    - Service role and UID
    - Network and subnet information
    - Registration status
    - Port configurations
    - Hotkey information

    Args:
        role: Service role ("validator" or "miner")
        uid: Assigned UID on the network
        hotkey: Name of the hotkey
        registered: Whether the service is registered
        network: Network name ("test" or "finney")
        netuid: Network UID
        axon_port: Port for axon server
        metrics_port: Port for Prometheus metrics
        grafana_port: Port for Grafana dashboard

    Note:
        Uses different icons for validator (🔍) and miner (⛏️)
    """
    icon = "🔍" if role == "validator" else "⛏️ "
    role_title = role.capitalize()

    print(f"\n=== {icon} {role_title} Status Report ===\n")
    print("-" * 50)
    print(
        f"""
• {role_title} {uid}
  ├─ Network: {network}
  ├─ Subnet: {netuid}
  ├─ {'✅ Running' if uid else '❌ Not Running'}
  ├─ {'✅ Registered' if registered else '❌ Not Registered'}
  ├─ Axon Port: {axon_port}
  ├─ Metrics Port: {metrics_port}
  └─ Grafana Port: {grafana_port}
  └─ Hotkey: {hotkey}

Starting Masa {role} process...
"""
    )


def main() -> None:
    """Main entry point for service startup.

    This function:
    1. Gets configuration from environment
    2. Sets up wallet and registration
    3. Configures ports based on role
    4. Prints status report
    5. Executes appropriate service

    Environment variables determine the role and configuration.
    The function will exit if any required variables are missing
    or if service startup fails.

    Raises:
        Exception: If service fails to start
        ValueError: If required environment variables are missing
    """
    try:
        # Get environment variables
        role = os.getenv("ROLE", "validator").lower()
        network = os.getenv("SUBTENSOR_NETWORK", "test").lower()
        netuid = int(os.getenv("NETUID"))
        replica_num = os.environ.get("REPLICA_NUM", "1")

        logger.info(f"Starting {role} on {network} network (netuid: {netuid})")

        # Calculate and export dynamic values
        hotkey_wallet = f"subnet_{netuid}"
        hotkey_name = f"{role}_{replica_num}"

        # Export these for use by the container
        os.environ["HOTKEY_WALLET"] = hotkey_wallet
        os.environ["HOTKEY_NAME"] = hotkey_name

        logger.info(f"Using wallet: {hotkey_wallet}, hotkey: {hotkey_name}")

        # Get Docker container ID
        container_id = os.popen("cat /proc/1/cpuset").read().strip().split("/")[-1]
        logger.info(f"Container ID: {container_id}")

        # Get target (internal) ports based on role
        if role == "validator":
            target_axon_port = int(os.getenv("VALIDATOR_AXON_PORT"))
            target_metrics_port = int(os.getenv("VALIDATOR_METRICS_PORT"))
            target_grafana_port = int(os.getenv("VALIDATOR_GRAFANA_PORT"))
        else:
            target_axon_port = int(os.getenv("MINER_AXON_PORT"))
            target_metrics_port = int(os.getenv("MINER_METRICS_PORT"))
            target_grafana_port = int(os.getenv("MINER_GRAFANA_PORT"))

        logger.info(
            "Target (internal) ports - "
            f"Axon: {target_axon_port}, "
            f"Metrics: {target_metrics_port}, "
            f"Grafana: {target_grafana_port}"
        )

        # Get published ports from Docker Swarm environment
        published_axon_port = int(os.getenv("PUBLISHED_AXON_PORT", target_axon_port))
        published_metrics_port = int(
            os.getenv("PUBLISHED_METRICS_PORT", target_metrics_port)
        )
        published_grafana_port = int(
            os.getenv("PUBLISHED_GRAFANA_PORT", target_grafana_port)
        )

        # Export the axon port for use by the container
        os.environ["AXON_PORT"] = str(published_axon_port)

        logger.info(
            "Published (external) ports - "
            f"Axon: {published_axon_port}, "
            f"Metrics: {published_metrics_port}, "
            f"Grafana: {published_grafana_port}"
        )

        # Set environment variables for registration and external access
        os.environ["METRICS_PORT"] = str(published_metrics_port)
        os.environ["GRAFANA_PORT"] = str(published_grafana_port)

        logger.info("Environment variables set:")
        logger.info(f"HOTKEY_WALLET={os.environ['HOTKEY_WALLET']}")
        logger.info(f"HOTKEY_NAME={os.environ['HOTKEY_NAME']}")
        logger.info(f"AXON_PORT={os.environ['AXON_PORT']}")
        logger.info(f"METRICS_PORT={os.environ['METRICS_PORT']}")
        logger.info(f"GRAFANA_PORT={os.environ['GRAFANA_PORT']}")

        # Initialize managers
        logger.info(f"Initializing {role} wallet manager...")
        wallet_manager = WalletManager(role=role, network=network, netuid=netuid)
        process_manager = ProcessManager()

        # Load wallet - this also checks registration
        logger.info("Loading wallet and checking registration...")
        wallet = wallet_manager.load_wallet()
        logger.info(f"Wallet loaded successfully: {wallet.hotkey.ss58_address}")

        # Get UID from subtensor
        logger.info("Retrieving UID from subtensor...")
        subtensor = bt.subtensor(network="test" if network == "test" else None)
        uid = subtensor.get_uid_for_hotkey_on_subnet(
            hotkey_ss58=wallet.hotkey.ss58_address,
            netuid=netuid,
        )
        logger.info(f"Retrieved UID: {uid}")

        # Print status using target ports
        print_status_report(
            role=role,
            uid=uid,
            hotkey=wallet_manager.hotkey_name,
            registered=True,
            network=network,
            netuid=netuid,
            axon_port=target_axon_port,
            metrics_port=target_metrics_port,
            grafana_port=target_grafana_port,
        )

        # Build and execute command
        if role == "validator":
            command = process_manager.build_validator_command(
                netuid=netuid,
                network=network,
                wallet_name=hotkey_wallet,
                wallet_hotkey=hotkey_name,
                logging_dir="/root/.bittensor/logs",
                axon_port=target_axon_port,
                prometheus_port=target_metrics_port,
                grafana_port=target_grafana_port,
            )
            logger.info(f"Executing validator command: {command}")
            process_manager.execute_validator(command)
        else:
            command = process_manager.build_miner_command(
                wallet_name=hotkey_wallet,
                wallet_hotkey=hotkey_name,
                netuid=netuid,
                network=network,
                logging_dir="/root/.bittensor/logs",
                axon_port=target_axon_port,
                prometheus_port=target_metrics_port,
                grafana_port=target_grafana_port,
            )
            logger.info(f"Executing miner command: {command}")
            process_manager.execute_miner(command)

    except Exception as e:
        logger.error(f"Failed to start {role}: {str(e)}")
        raise


if __name__ == "__main__":
    main()
