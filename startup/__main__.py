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
    """Print a formatted status report for the service."""
    icon = "🔍" if role == "validator" else "⛏️"
    role_title = role.capitalize()
    status = "✅ Active" if uid else "❌ Inactive"
    reg_status = "✅ Registered" if registered else "❌ Not Registered"

    print(f"\n{icon} {role_title} Status")
    print("─" * 40)
    print(f"Network: {network.upper()} (Subnet {netuid})")
    print(f"Status: {status}")
    print(f"Registration: {reg_status}")
    print(f"UID: {uid}")
    print(f"Hotkey: {hotkey}")
    print("\nPorts:")
    print(f"  Axon: {axon_port}")
    print(f"  Metrics: {metrics_port}")
    print(f"  Grafana: {grafana_port}")
    print("─" * 40)
    print(f"\nStarting {role_title} process...")


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
        role = os.getenv("ROLE").lower()
        network = os.getenv("SUBTENSOR_NETWORK").lower()
        netuid = int(os.getenv("NETUID"))
        replica_num = os.environ.get("REPLICA_NUM", "1")

        logger.info(f"Starting {role} on {network} network (netuid: {netuid})")

        # Get wallet name from env, generate hotkey name dynamically
        wallet_name = os.getenv("WALLET_NAME")
        hotkey_name = f"{role}_{replica_num}"

        # Export these for use by the container
        if role == "validator":
            os.environ["VALIDATOR_WALLET_NAME"] = wallet_name
            os.environ["VALIDATOR_HOTKEY_NAME"] = hotkey_name
            target_axon_port = int(os.getenv("VALIDATOR_AXON_PORT"))
            target_metrics_port = int(os.getenv("VALIDATOR_METRICS_PORT"))
            target_grafana_port = int(os.getenv("VALIDATOR_GRAFANA_PORT"))

        else:
            target_axon_port = int(os.getenv("MINER_AXON_PORT"))
            target_metrics_port = int(os.getenv("MINER_METRICS_PORT"))
            target_grafana_port = int(os.getenv("MINER_GRAFANA_PORT"))
            os.environ["WALLET_NAME"] = wallet_name
            os.environ["HOTKEY_NAME"] = hotkey_name
            # Only set MINER_PORT if not already set
            if "MINER_PORT" not in os.environ:
                os.environ["MINER_PORT"] = str(target_axon_port)

        # Get published ports from Docker Swarm environment
        published_axon_port = int(os.getenv("PUBLISHED_AXON_PORT", target_axon_port))
        published_metrics_port = int(
            os.getenv("PUBLISHED_METRICS_PORT", target_metrics_port)
        )
        published_grafana_port = int(
            os.getenv("PUBLISHED_GRAFANA_PORT", target_grafana_port)
        )

        # Export ports for use by the container
        os.environ["AXON_PORT"] = str(published_axon_port)
        os.environ["METRICS_PORT"] = str(published_metrics_port)
        os.environ["GRAFANA_PORT"] = str(published_grafana_port)

        logger.info(f"Configuration: Wallet={wallet_name}, Hotkey={hotkey_name}")
        logger.info(
            f"Ports: Axon={published_axon_port}, Metrics={published_metrics_port}, Grafana={published_grafana_port}"
        )

        # Initialize managers
        wallet_manager = WalletManager(role=role, network=network, netuid=netuid)
        process_manager = ProcessManager()

        # Load wallet and check registration
        wallet = wallet_manager.load_wallet()

        # Get UID from subtensor
        subtensor = bt.subtensor(network=network)
        uid = subtensor.get_uid_for_hotkey_on_subnet(
            hotkey_ss58=wallet.hotkey.ss58_address,
            netuid=netuid,
        )
        logger.info(f"Node registered with UID: {uid}")

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
                wallet_name=wallet_name,
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
                wallet_name=wallet_name,
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
