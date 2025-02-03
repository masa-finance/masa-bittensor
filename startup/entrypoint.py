import os
import logging
import asyncio
import bittensor as bt
from startup.wallet_manager import WalletManager
from startup.registration_manager import RegistrationManager
from startup.process_manager import ProcessManager
from startup.config import get_chain_endpoint, get_mainnet_netuid

# Print all environment variables at startup
print("=== PYTHON ENVIRONMENT VARIABLES ===")
for key, value in sorted(os.environ.items()):
    print(f"{key}={value}")
print("==================================")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Orchestrator:
    """Orchestrates the startup and initialization of validator/miner nodes."""

    def __init__(self):
        """Initialize the orchestrator with configuration from environment."""
        # Get network configuration
        self.network = os.environ["NETWORK"].split("#")[0].strip()
        self.role = os.environ.get("ROLE", "validator")

        # Determine NETUID based on network
        self.netuid = 165 if self.network == "test" else 42

        # Map network and subnet IDs
        self.chain_endpoint = get_chain_endpoint(self.network)
        if not self.chain_endpoint:
            raise ValueError(f"Invalid network: {self.network}")

        # Set up wallet names
        self.wallet_name = f"subnet_{self.netuid}"

        # Get service name and replica number from Docker environment
        service_name = os.environ.get("SERVICE_NAME", "")
        replica_num = os.environ.get("REPLICA_NUM", "")

        try:
            self.replica_num = int(replica_num) if replica_num else 1
        except ValueError:
            print(f"Warning: Invalid replica number: {replica_num}")
            self.replica_num = 1

        print(f"Service: {service_name}, Replica: {self.replica_num}")  # Debug print
        self.wallet_hotkey = f"{self.role}_{self.replica_num}"

        # Calculate ports
        self.port, self.metrics_port = self._calculate_ports()

        # Log configuration
        mainnet_id = (
            get_mainnet_netuid(str(self.netuid))
            if self.network == "test"
            else str(self.netuid)
        )
        logger.info(
            "Initializing %s with wallet %s/%s on port %d with metrics on port %d",
            self.role,
            self.wallet_name,
            self.wallet_hotkey,
            self.port,
            self.metrics_port,
        )
        logger.info(
            "Network: %s (endpoint: %s), Subnet: %s (maps to mainnet: %s)",
            self.network,
            self.chain_endpoint,
            self.netuid,
            mainnet_id,
        )

    def _calculate_ports(self) -> tuple[int, int]:
        """Calculate service and metrics ports based on role and replica number."""
        if self.role == "validator":
            if self.replica_num > 64:
                raise ValueError("Validator replica number cannot exceed 64")
            base_port = int(os.environ.get("VALIDATOR_PORT", "8091"))
            base_metrics_port = int(os.environ.get("VALIDATOR_METRICS_PORT", "9100"))
        else:  # miner
            if self.replica_num > 255:
                raise ValueError("Miner replica number cannot exceed 255")
            base_port = int(os.environ.get("MINER_PORT", "8155"))
            base_metrics_port = int(os.environ.get("MINER_METRICS_PORT", "9164"))

        return base_port + (self.replica_num - 1), base_metrics_port + (
            self.replica_num - 1
        )

    async def setup_and_run(self):
        """Set up the node and run it."""
        try:
            # Initialize managers
            wallet_manager = WalletManager(
                wallet_name=self.wallet_name,
                hotkey=self.wallet_hotkey,
                netuid=self.netuid,
                network=self.network,
            )

            # Set up wallet directories and initialize wallet
            wallet_manager.setup_wallet_directories()
            wallet = wallet_manager.initialize_wallet(
                coldkey_mnemonic=os.environ.get("COLDKEY_MNEMONIC"),
                is_validator=(self.role == "validator"),
            )

            # Set up subtensor connection
            config = bt.config()
            config.netuid = self.netuid
            config.no_prompt = True

            # Only set network-specific config for test network
            if self.network == "test":
                config.subtensor = bt.subtensor.config()
                config.subtensor.network = "test"
                config.subtensor.chain_endpoint = self.chain_endpoint

            subtensor = bt.subtensor(config=config)
            registration_manager = RegistrationManager(subtensor)

            # Handle registration
            success, uid = registration_manager.register_if_needed(
                wallet=wallet,
                netuid=self.netuid,
                is_validator=(self.role == "validator"),
            )

            if success:
                # Update mappings
                wallet_manager.update_hotkey_mappings(wallet, uid, self.role)
                # Verify registration
                registration_manager.verify_registration_status(wallet, self.netuid)

                # Initialize process manager and run the appropriate process
                process_manager = ProcessManager()

                if self.role == "validator":
                    command = process_manager.build_validator_command(
                        netuid=self.netuid,
                        network=self.network,
                        wallet_name=self.wallet_name,
                        wallet_hotkey=self.wallet_hotkey,
                        axon_port=self.port,
                        prometheus_port=self.metrics_port,
                    )
                    process_manager.execute_validator(command)
                else:
                    command = process_manager.build_miner_command(
                        netuid=self.netuid,
                        network=self.network,
                        wallet_name=self.wallet_name,
                        wallet_hotkey=self.wallet_hotkey,
                        axon_port=self.port,
                        prometheus_port=self.metrics_port,
                    )
                    process_manager.execute_miner(command)

        except Exception as e:
            logger.error(f"Error in {self.role} setup and execution: {e}")
            raise


if __name__ == "__main__":
    orchestrator = Orchestrator()
    asyncio.run(orchestrator.setup_and_run())
