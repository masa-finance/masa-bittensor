import os
import json
import logging
import bittensor as bt
from neurons.validator import Validator

# Remove prometheus imports
# from prometheus_client import start_http_server, Gauge, Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set bittensor logging to WARNING to suppress wallet messages
bt.logging.set_trace(True)
bt.logging.set_debug(True)
bt.logging.set_level(level="WARNING")


class Orchestrator:
    def __init__(self):
        self.config_path = os.getenv("CONFIG_PATH", "subnet-config.json")
        self.config = self.load_config()
        self.validator = None
        # Use container name as hotkey
        self.container_id = os.environ.get("HOSTNAME", "validator_default")

    def load_config(self) -> dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config from {self.config_path}: {e}")
            return {}

    def setup_repo(self):
        """Set up the repository with wallet configuration."""
        try:
            # Create wallet config using subnet config structure
            wallet_config = bt.config()
            wallet_config.wallet.name = self.config["wallet"][
                "name"
            ]  # Should be "default"
            wallet_config.wallet.hotkey = (
                self.container_id
            )  # Use container ID as hotkey

            # Set network and netuid from config
            wallet_config.netuid = self.config["subtensor"]["netuid"]
            wallet_config.subtensor.network = self.config["subtensor"]["network"]

            # Set logging from config
            wallet_config.logging.debug = self.config["logging"]["debug"]
            wallet_config.logging.file_logging = self.config["logging"]["file_logging"]
            if self.config["logging"]["file_logging"]:
                wallet_config.logging.logging_dir = self.config["logging"][
                    "logging_dir"
                ]

            # Initialize the validator with our config
            self.validator = Validator(config=wallet_config)
            logging.info(
                f"Successfully set up validator with wallet default/{self.container_id}"
            )

        except Exception as e:
            logging.error(f"Failed to setup repository: {e}")
            raise

    def run(self):
        """Run the validator."""
        try:
            if not self.validator:
                self.setup_repo()

            # Use the context manager to properly handle the validator lifecycle
            with self.validator:
                logging.info("Starting validator...")
                # The validator will run in background threads
                while True:
                    import time

                    time.sleep(5)  # Keep the main thread alive

        except Exception as e:
            logging.error(f"Error running validator: {e}")
            raise


if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run()
