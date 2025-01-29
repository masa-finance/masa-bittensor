import os
import logging
import asyncio
import json
import bittensor as bt
from neurons.validator import Validator
from contextlib import redirect_stdout
import subprocess

# Remove prometheus imports
# from prometheus_client import start_http_server, Gauge, Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        netuid = os.environ["NETUID"]
        self.wallet_name = f"subnet_{netuid}"  # Use subnet ID for wallet name
        role = os.environ.get("ROLE", "validator")
        # Docker Swarm sets HOSTNAME to container_name-replica_number
        # But in compose it's service_name-N-container_id
        # Extract N from the middle
        hostname = os.environ.get("HOSTNAME", "")
        replica = (
            hostname.split("-")[1] if hostname and len(hostname.split("-")) > 2 else "1"
        )
        self.replica_num = int(replica)
        self.wallet_hotkey = f"{role}_{replica}"
        self.validator = None

        # Calculate ports based on role and replica number
        if role == "validator":
            base_port = int(os.environ.get("VALIDATOR_PORT", "8091"))
            base_metrics_port = int(os.environ.get("VALIDATOR_METRICS_PORT", "9100"))
            # Ensure replica number is within validator range (max 64 replicas)
            if self.replica_num > 64:
                raise ValueError("Validator replica number cannot exceed 64")
            self.port = base_port + (self.replica_num - 1)
            self.metrics_port = base_metrics_port + (self.replica_num - 1)
        else:  # miner
            base_port = int(os.environ.get("MINER_PORT", "8155"))
            base_metrics_port = int(os.environ.get("MINER_METRICS_PORT", "9164"))
            # Ensure replica number is within miner range (max 255 replicas)
            if self.replica_num > 255:
                raise ValueError("Miner replica number cannot exceed 255")
            self.port = base_port + (self.replica_num - 1)
            self.metrics_port = base_metrics_port + (self.replica_num - 1)

        logging.info(
            "Initializing %s with wallet %s/%s on port %d with metrics on port %d",
            role,
            self.wallet_name,
            self.wallet_hotkey,
            self.port,
            self.metrics_port,
        )

    async def setup_repo(self):
        """Set up the repository with wallet configuration."""
        try:
            # Create config first
            config = bt.config()
            config.subtensor = bt.subtensor.config()
            # Strip any comments from network value (everything after #)
            network = os.environ["NETWORK"].split("#")[0].strip()
            # Strip any comments from netuid value
            netuid = os.environ["NETUID"].split("#")[0].strip()
            config.subtensor.network = network
            config.subtensor.netuid = int(netuid)
            config.netuid = int(netuid)  # Set netuid in both places
            config.network = network  # Set network in top level config
            config.no_prompt = True

            # Ensure wallet directory exists with proper permissions
            wallet_dir = os.path.expanduser(f"~/.bittensor/wallets/{self.wallet_name}")
            os.makedirs(wallet_dir, mode=0o700, exist_ok=True)
            os.makedirs(os.path.join(wallet_dir, "hotkeys"), mode=0o700, exist_ok=True)

            # Initialize wallet with explicit parameters
            wallet = bt.wallet(
                name=self.wallet_name,
                hotkey=self.wallet_hotkey,
                path=os.path.expanduser("~/.bittensor/wallets/"),
            )

            # First check if coldkey exists in the subnet-specific directory
            coldkey_path = os.path.join(wallet.path, self.wallet_name, "coldkey")
            if os.path.exists(coldkey_path):
                logging.info("Found coldkey at %s", coldkey_path)
            else:
                # Only regenerate coldkey if no coldkey exists and we're a validator
                if os.environ.get("ROLE") == "validator":
                    if not os.environ.get("COLDKEY_MNEMONIC"):
                        raise Exception(
                            "No coldkey found and COLDKEY_MNEMONIC not provided for validator"
                        )
                    logging.info(
                        "No coldkey found, attempting to regenerate from mnemonic"
                    )

                    # Completely suppress all output during regeneration
                    with open(os.devnull, "w") as devnull:
                        with redirect_stdout(devnull):
                            try:
                                wallet.regenerate_coldkey(
                                    mnemonic=os.environ["COLDKEY_MNEMONIC"],
                                    use_password=False,
                                    overwrite=False,  # Never overwrite existing
                                )
                            except Exception as e:
                                if "already exists" in str(e):
                                    logging.info(
                                        "Coldkey already exists, skipping regeneration"
                                    )
                                else:
                                    raise

                    logging.info("Successfully regenerated coldkey from mnemonic")
                else:
                    logging.info("No coldkey found but not needed for miner")

            # At this point we have a wallet (either existed or we created it)
            # Now we can check hotkey, registration etc.
            subtensor = bt.subtensor(config=config)
            logging.info(
                "First subtensor config: %s",
                {
                    "network": subtensor.network,
                    "chain_endpoint": subtensor.chain_endpoint or "default",
                },
            )

            # Check if hotkey exists in the subnet-specific directory
            hotkey_path = os.path.join(
                wallet.path, self.wallet_name, "hotkeys", self.wallet_hotkey
            )
            if os.path.exists(hotkey_path):
                logging.info("Found existing hotkey at %s", hotkey_path)
            else:
                logging.info("Creating new hotkey %s", self.wallet_hotkey)
                # Suppress stdout during sensitive operations
                with open(os.devnull, "w") as devnull:
                    with redirect_stdout(devnull):
                        try:
                            wallet.create_new_hotkey(
                                use_password=False,
                                overwrite=False,  # Never overwrite existing
                            )
                        except Exception as e:
                            if "already exists" in str(e):
                                logging.info("Hotkey already exists, skipping creation")
                            else:
                                raise

                logging.info("Successfully created new hotkey %s", self.wallet_hotkey)

            # Check registration status
            is_registered = subtensor.is_hotkey_registered(
                netuid=config.subtensor.netuid,
                hotkey_ss58=wallet.hotkey.ss58_address,
            )

            if is_registered:
                uid = subtensor.get_uid_for_hotkey_on_subnet(
                    hotkey_ss58=wallet.hotkey.ss58_address,
                    netuid=config.subtensor.netuid,
                )
                logging.info("Hotkey is registered with UID %s", uid)

                # Update hotkey mappings file
                mappings_file = os.path.expanduser("~/.bt-masa/hotkey_mappings.json")
                os.makedirs(os.path.dirname(mappings_file), mode=0o700, exist_ok=True)

                # Load existing mappings
                mappings = {}
                if os.path.exists(mappings_file):
                    try:
                        with open(mappings_file, "r") as f:
                            mappings = json.load(f)
                    except json.JSONDecodeError:
                        logging.warning(
                            "Could not parse existing mappings file, starting fresh"
                        )

                # Update mappings with current hotkey info
                mappings[wallet.hotkey.ss58_address] = {
                    "uid": uid,
                    "role": os.environ.get("ROLE", "validator"),
                    "netuid": config.subtensor.netuid,
                    "wallet_name": self.wallet_name,
                    "hotkey_name": self.wallet_hotkey,
                }

                # Save updated mappings
                with open(mappings_file, "w") as f:
                    json.dump(mappings, f, indent=2)
                logging.info("Updated hotkey mappings in %s", mappings_file)

                # Add more detailed registration checks
                logging.info("Double checking registration status:")
                logging.info(f"Checking netuid {config.subtensor.netuid}")
                logging.info(f"Hotkey address: {wallet.hotkey.ss58_address}")

                # Check registration on any subnet
                any_subnet = subtensor.is_hotkey_registered_any(
                    wallet.hotkey.ss58_address
                )
                logging.info(f"Is registered on any subnet: {any_subnet}")

                # Check specific subnet registration again
                subnet_check = subtensor.is_hotkey_registered_on_subnet(
                    wallet.hotkey.ss58_address, config.subtensor.netuid
                )
                logging.info(
                    f"Is registered on subnet {config.subtensor.netuid}: {subnet_check}"
                )

            else:
                logging.info("Hotkey exists but is not registered")
                if os.environ.get("ROLE") == "validator":
                    # For validators, use burned registration
                    logging.info(
                        "Starting burned registration process for validator hotkey"
                    )

                    # Check current balance
                    balance = subtensor.get_balance(wallet.coldkeypub.ss58_address)
                    logging.info(f"Current balance: {balance} TAO")

                    # Get registration cost
                    cost = subtensor.recycle(config.subtensor.netuid)
                    logging.info(f"Registration cost: {cost} TAO")

                    if balance < cost:
                        raise Exception(
                            f"Insufficient balance ({balance} TAO) for registration. Need {cost} TAO"
                        )

                    logging.info("Balance sufficient for registration, proceeding...")
                    logging.info(
                        f"This process will burn {cost} TAO from your balance of {balance} TAO"
                    )
                    logging.info("Starting registration (this may take a few minutes)")

                    # First check if registration is still needed
                    if subtensor.is_hotkey_registered(
                        netuid=config.subtensor.netuid,
                        hotkey_ss58=wallet.hotkey.ss58_address,
                    ):
                        logging.info(
                            "Hotkey was registered by another process, continuing..."
                        )
                        success = True
                    else:
                        logging.info("Calling burned_register...")
                        success = subtensor.burned_register(
                            wallet=wallet,
                            netuid=config.subtensor.netuid,
                            wait_for_inclusion=True,
                            wait_for_finalization=True,
                        )
                        logging.info("burned_register call completed")

                    if not success:
                        raise Exception(
                            "Failed to register validator hotkey - check subnet and balance"
                        )

                    # Verify registration
                    is_registered = subtensor.is_hotkey_registered(
                        netuid=config.subtensor.netuid,
                        hotkey_ss58=wallet.hotkey.ss58_address,
                    )

                    if is_registered:
                        new_balance = subtensor.get_balance(
                            wallet.coldkeypub.ss58_address
                        )
                        uid = subtensor.get_uid_for_hotkey_on_subnet(
                            hotkey_ss58=wallet.hotkey.ss58_address,
                            netuid=config.subtensor.netuid,
                        )
                        logging.info(
                            f"Successfully registered validator hotkey with UID {uid}"
                        )
                        logging.info(
                            f"New balance after registration: {new_balance} TAO (burned {balance - new_balance} TAO)"
                        )
                    else:
                        raise Exception(
                            "Registration appeared to succeed but hotkey is not registered"
                        )
                else:
                    # For miners, attempt registration
                    logging.info("Attempting to register miner hotkey...")
                    # Check current balance
                    balance = subtensor.get_balance(wallet.coldkeypub.ss58_address)
                    logging.info(f"Current balance: {balance} TAO")

                    # Get registration cost
                    cost = subtensor.recycle(config.subtensor.netuid)
                    logging.info(f"Registration cost: {cost} TAO")

                    if balance < cost:
                        raise Exception(
                            f"Insufficient balance ({balance} TAO) for registration. Need {cost} TAO"
                        )

                    logging.info("Balance sufficient for registration, proceeding...")
                    logging.info(
                        f"This process will burn {cost} TAO from your balance of {balance} TAO"
                    )
                    logging.info("Starting registration (this may take a few minutes)")

                    # First check if registration is still needed
                    if subtensor.is_hotkey_registered(
                        netuid=config.subtensor.netuid,
                        hotkey_ss58=wallet.hotkey.ss58_address,
                    ):
                        logging.info(
                            "Hotkey was registered by another process, continuing..."
                        )
                        success = True
                    else:
                        logging.info("Calling burned_register...")
                        success = subtensor.burned_register(
                            wallet=wallet,
                            netuid=config.subtensor.netuid,
                            wait_for_inclusion=True,
                            wait_for_finalization=True,
                        )
                        logging.info("burned_register call completed")

                    if not success:
                        raise Exception(
                            "Failed to register miner hotkey - check subnet and balance"
                        )

                    # Verify registration
                    is_registered = subtensor.is_hotkey_registered(
                        netuid=config.subtensor.netuid,
                        hotkey_ss58=wallet.hotkey.ss58_address,
                    )

                    if is_registered:
                        new_balance = subtensor.get_balance(
                            wallet.coldkeypub.ss58_address
                        )
                        uid = subtensor.get_uid_for_hotkey_on_subnet(
                            hotkey_ss58=wallet.hotkey.ss58_address,
                            netuid=config.subtensor.netuid,
                        )
                        logging.info(
                            f"Successfully registered miner hotkey with UID {uid}"
                        )
                        logging.info(
                            f"New balance after registration: {new_balance} TAO (burned {balance - new_balance} TAO)"
                        )

            # Initialize the validator with our config (only for validators)
            if os.environ.get("ROLE") == "validator":
                # Set up wallet config properly
                config.wallet = bt.config()
                config.wallet.name = self.wallet_name
                config.wallet.hotkey = self.wallet_hotkey
                config.wallet.path = os.path.expanduser("~/.bittensor/wallets/")
                config.wallet.network = network  # Use cleaned network value

                # Copy chain endpoint to all configs
                config.chain_endpoint = subtensor.chain_endpoint
                config.wallet.chain_endpoint = subtensor.chain_endpoint
                config.subtensor.chain_endpoint = subtensor.chain_endpoint

                # Ensure netuid is set in all configs
                config.netuid = int(os.environ["NETUID"])
                config.wallet.netuid = int(os.environ["NETUID"])

                # Log full config before creating validator
                logging.info(
                    "Validator config: %s",
                    {
                        "network": config.network,
                        "netuid": config.netuid,
                        "wallet.network": config.wallet.network,
                        "wallet.netuid": config.wallet.netuid,
                        "subtensor.network": config.subtensor.network,
                        "subtensor.netuid": config.subtensor.netuid,
                        "chain_endpoint": getattr(config, "chain_endpoint", None),
                    },
                )

                self.validator = Validator(config=config)
                logging.info(
                    f"Successfully set up validator with wallet {self.wallet_name}/{self.wallet_hotkey} for netuid {config.netuid}"
                )

        except Exception as e:
            logging.error(f"Failed to setup repository: {e}")
            raise

    async def run(self):
        """Run the validator or miner."""
        # Define role at the start to ensure it's available in error handling
        role = os.environ.get("ROLE", "validator")

        try:
            # First do all the wallet setup and registration
            await self.setup_repo()

            # Now start the actual validator/miner process
            netuid = os.environ["NETUID"]
            # Clean network value
            network = os.environ["NETWORK"].split("#")[0].strip()

            logging.info(
                "Starting %s process (replica %d) on port %d with metrics on port %d",
                role,
                self.replica_num,
                self.port,
                self.metrics_port,
            )

            if role == "validator":
                # Run validator process
                wallet_path = os.path.expanduser("~/.bittensor/wallets/")
                # Set up state directory for validator
                state_path = os.path.expanduser(f"~/.bittensor/states")
                os.makedirs(state_path, mode=0o700, exist_ok=True)

                # Build validator command
                validator_command = [
                    "python",
                    "neurons/validator.py",
                    f"--netuid={netuid}",
                    f"--subtensor.network={network}",
                    f"--wallet.name={self.wallet_name}",
                    f"--wallet.hotkey={self.wallet_hotkey}",
                    f"--wallet.path={wallet_path}",
                    f"--logging.logging_dir={state_path}",
                    f"--axon.port={self.port}",
                    f"--prometheus.port={self.metrics_port}",
                    "--logging.debug",
                ]

                # Execute validator
                logging.info(f"Executing command: {' '.join(validator_command)}")
                os.execvp(validator_command[0], validator_command)
            else:
                # Run miner process
                wallet_path = os.path.expanduser("~/.bittensor/wallets/")
                # Set up state directory for miner
                state_path = os.path.expanduser(f"~/.bittensor/states")
                os.makedirs(state_path, mode=0o700, exist_ok=True)

                # Build miner command
                miner_command = [
                    "python",
                    "neurons/miner.py",
                    f"--netuid={netuid}",
                    f"--subtensor.network={network}",
                    f"--wallet.name={self.wallet_name}",
                    f"--wallet.hotkey={self.wallet_hotkey}",
                    f"--wallet.path={wallet_path}",
                    f"--logging.logging_dir={state_path}",
                    f"--axon.port={self.port}",
                    f"--prometheus.port={self.metrics_port}",
                    "--logging.debug",
                    "--blacklist.force_validator_permit",
                ]

                # Execute miner
                logging.info(f"Executing miner command: {' '.join(miner_command)}")
                subprocess.run(miner_command)

        except Exception as e:
            logging.error(f"Error running {role}: {e}")
            raise


if __name__ == "__main__":
    orchestrator = Orchestrator()
    asyncio.run(orchestrator.run())
