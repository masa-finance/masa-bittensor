import os
import json
import logging
import bittensor as bt
from typing import Optional

# Remove prometheus imports
# from prometheus_client import start_http_server, Gauge, Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set bittensor logging to WARNING to suppress wallet messages
bt.logging.set_trace(False)
bt.logging.set_debug(False)
bt_logger = logging.getLogger("bittensor")
bt_logger.setLevel(logging.WARNING)


class NodeOrchestrator:
    def __init__(self):
        self.role = os.environ.get("ROLE", "validator")
        self.network = os.environ.get("NETWORK", "test")
        self.netuid = int(os.environ.get("NETUID", "249"))
        self.config_path = os.environ.get("CONFIG_PATH", "subnet-config.json")
        self.wallet_name = os.environ.get("WALLET_NAME", "default")
        # Use local .bittensor directory
        self.wallet_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".bittensor/wallets"
        )
        os.makedirs(self.wallet_dir, exist_ok=True)
        self.wallet = None
        self.service_index = int(os.environ.get("SERVICE_INDEX", "0"))

        # Remove metrics setup
        # self.setup_metrics()

    # Remove metrics setup method
    # def setup_metrics(self):
    #     self.metrics_port = 9100 + self.service_index
    #     start_http_server(self.metrics_port)
    #     self.wallet_balance = Gauge('wallet_balance', 'Current wallet balance')
    #     self.registration_attempts = Counter('registration_attempts', 'Number of registration attempts')

    def setup_repo(self) -> Optional[bt.wallet]:
        try:
            # Get container name to use as hotkey name
            container_name = os.environ.get(
                "HOSTNAME", f"{self.role}_{self.service_index}"
            )
            logger.info(f"Using container name as hotkey: {container_name}")

            # Temporarily increase log level during wallet operations
            prev_level = bt_logger.level
            bt_logger.setLevel(logging.ERROR)

            # Initialize wallet with default hotkey first
            self.wallet = bt.wallet(name=self.wallet_name)

            # Check if hotkey exists
            hotkey_path = os.path.join(
                self.wallet_dir, self.wallet_name, "hotkeys", container_name
            )
            if not os.path.exists(hotkey_path):
                logger.info(f"Creating new hotkey: {container_name}")
                self.wallet.create_new_hotkey(use_password=False)
                # Rename the default hotkey file to our container name
                default_path = os.path.join(
                    self.wallet_dir, self.wallet_name, "hotkeys", "default"
                )
                if os.path.exists(default_path):
                    os.rename(default_path, hotkey_path)
                logger.info(f"Successfully created hotkey: {container_name}")
            else:
                logger.info(f"Using existing hotkey: {container_name}")
                # Set the wallet to use our container's hotkey
                self.wallet.set_hotkey(container_name)

            # Restore previous log level
            bt_logger.setLevel(prev_level)
            return self.wallet

        except Exception as e:
            logger.error(f"Failed to setup repo: {str(e)}")
            return None

    def run(self):
        try:
            # Setup wallet
            if not self.setup_repo():
                logger.error("Failed to setup repo")
                return

            # Load config
            with open(self.config_path) as f:
                config = json.load(f)

            # Get coldkey mnemonic from environment
            coldkey_mnemonic = os.environ.get("COLDKEY_MNEMONIC")
            if not coldkey_mnemonic:
                logger.error("COLDKEY_MNEMONIC not set")
                return

            # Check if coldkey exists
            coldkey_path = os.path.join(self.wallet_dir, self.wallet_name, "coldkey")
            if not os.path.exists(coldkey_path):
                # Temporarily increase log level during wallet operations
                prev_level = bt_logger.level
                bt_logger.setLevel(logging.ERROR)

                # Regenerate coldkey from mnemonic only if it doesn't exist
                self.wallet.regenerate_coldkey(coldkey_mnemonic)

                # Restore previous log level
                bt_logger.setLevel(prev_level)
            else:
                logger.info("Using existing coldkey")

            # Start role-specific process
            if self.role == "validator":
                from neurons.validator import run_validator

                run_validator(self.wallet, config)
            elif self.role == "miner":
                from neurons.miner import run_miner

                run_miner(self.wallet, config)
            else:
                logger.error(f"Unknown role: {self.role}")

        except Exception as e:
            logger.error(f"Failed to run {self.role}: {str(e)}")


if __name__ == "__main__":
    orchestrator = NodeOrchestrator()
    orchestrator.run()
