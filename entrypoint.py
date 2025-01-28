import os
import json
import logging
import asyncio
import bittensor as bt
from bittensor import subtensor, wallet, config
from neurons.validator import Validator

# Remove prometheus imports
# from prometheus_client import start_http_server, Gauge, Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
            logging.info(f"Attempting to load config from {self.config_path}")
            with open(self.config_path, "r") as f:
                config = json.load(f)
                logging.info(f"Successfully loaded config: {config}")
                return config
        except Exception as e:
            logging.error(f"Failed to load config from {self.config_path}: {e}")
            return {}

    def setup_repo(self):
        """Set up the repository with wallet configuration."""
        try:
            # Create wallet config with defaults
            config = bt.config()

            # Set wallet config
            config.wallet_name = "default"
            config.wallet_hotkey = self.container_id  # Use container ID as hotkey

            # Set subtensor config
            config.subtensor = bt.subtensor.config()
            config.subtensor.network = "test"
            config.subtensor.netuid = 249
            config.no_prompt = True  # Avoid any user prompts

            # Check if hotkey exists, create if it doesn't
            hotkey_path = (
                f"/root/.bittensor/wallets/default/hotkeys/{self.container_id}"
            )
            if not os.path.exists(hotkey_path):
                logging.info(f"Creating new hotkey {self.container_id}")
                wallet = bt.wallet(config=config)
                wallet.create_new_hotkey(use_password=False, overwrite=True)
            else:
                logging.info(f"Using existing hotkey {self.container_id}")

            # Create wallet and subtensor connection
            wallet = bt.wallet(config=config)
            subtensor = bt.subtensor(config=config)

            # Get current registration status
            is_registered = subtensor.is_hotkey_registered(
                netuid=config.subtensor.netuid, hotkey_ss58=wallet.hotkey.ss58_address
            )
            uid = None
            if is_registered:
                uid = subtensor.get_uid_for_hotkey_on_subnet(
                    hotkey_ss58=wallet.hotkey.ss58_address,
                    netuid=config.subtensor.netuid,
                )
                logging.info(
                    f"Hotkey {self.container_id} already registered with UID {uid}"
                )

            # Always attempt registration
            logging.info(f"Attempting registration on subnet {config.subtensor.netuid}")
            try:
                success = subtensor.register(
                    wallet=wallet,
                    netuid=config.subtensor.netuid,
                    wait_for_inclusion=True,
                    wait_for_finalization=True,
                    max_allowed_attempts=3,
                    output_in_place=True,
                    cuda=False,
                    dev_id=0,
                    tpb=256,
                    num_processes=None,
                    update_interval=None,
                    log_verbose=True,
                )
                if success:
                    # Get the UID after registration attempt
                    uid = subtensor.get_uid_for_hotkey_on_subnet(
                        hotkey_ss58=wallet.hotkey.ss58_address,
                        netuid=config.subtensor.netuid,
                    )
                    logging.info(f"Registration complete. UID: {uid}")
                else:
                    if is_registered:
                        logging.info(
                            f"Already registered with UID {uid}, continuing..."
                        )
                    else:
                        raise Exception("Registration failed")
            except Exception as reg_error:
                if is_registered:
                    logging.info(f"Already registered with UID {uid}, continuing...")
                else:
                    raise reg_error

            # Initialize the validator with our config
            self.validator = Validator(config=config)
            logging.info(
                f"Successfully set up validator with wallet default/{self.container_id}"
            )

        except Exception as e:
            logging.error(f"Failed to setup repository: {e}")
            raise

    async def run(self):
        """Run the validator."""
        try:
            if not self.validator:
                self.setup_repo()

            # Use the context manager to properly handle the validator lifecycle
            with self.validator:
                logging.info("Starting validator...")
                # The validator will run in background threads
                while True:
                    await asyncio.sleep(5)  # Keep the main thread alive

        except Exception as e:
            logging.error(f"Error running validator: {e}")
            raise


if __name__ == "__main__":
    orchestrator = Orchestrator()
    asyncio.run(orchestrator.run())
