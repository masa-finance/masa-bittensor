"""Wallet Manager Module.

This module handles all wallet-related operations for validators and miners in the Agent Arena subnet.
It manages wallet creation, loading, registration, and hotkey setup.

Example:
    >>> manager = WalletManager(role="validator", network="test", netuid=249)
    >>> wallet = manager.load_wallet()
    >>> uid = manager.register()
"""

import logging
import os
import json
import bittensor as bt
import time
from substrateinterface.exceptions import SubstrateRequestException
from typing import Optional

logger = logging.getLogger(__name__)


class WalletManager:
    """Manages wallet operations for validators and miners.

    This class handles all aspects of wallet management including:
    - Wallet creation and loading
    - Coldkey management from mnemonics
    - Hotkey creation and setup
    - Registration with the subnet
    - Hotkey mapping maintenance

    Attributes:
        role (str): Role of the node ("validator" or "miner")
        network (str): Network to connect to ("test" or "finney")
        netuid (int): Network UID to register on (249 for testnet, 59 for mainnet)
        wallet_name (str): Name of the wallet (format: "subnet_{netuid}")
        hotkey_name (str): Name of the hotkey (format: "{role}_{replica_num}")
        wallet (bt.wallet): The loaded bittensor wallet instance
        subtensor (bt.subtensor): Connection to the subtensor network
    """

    def __init__(self, role: str, network: str, netuid: int):
        """Initialize the wallet manager.

        Args:
            role: Role of the node ("validator" or "miner")
            network: Network to connect to ("test" or "finney")
            netuid: Network UID to register on (249 for testnet, 59 for mainnet)

        Raises:
            ValueError: If role is not "validator" or "miner"
            ValueError: If network is not "test" or "finney"
            ValueError: If HOTKEY_WALLET or HOTKEY_NAME env vars are not set
        """
        self.role = role
        self.network = network
        self.netuid = netuid
        self.logger = logging.getLogger(__name__)
        self.subtensor = None

        # Get wallet and hotkey names from environment
        self.wallet_name = os.environ.get("HOTKEY_WALLET")
        self.hotkey_name = os.environ.get("HOTKEY_NAME")

        if not self.wallet_name or not self.hotkey_name:
            raise ValueError(
                "HOTKEY_WALLET and HOTKEY_NAME environment variables must be set"
            )

        self.logger.info(
            f"Using wallet: {self.wallet_name}, hotkey: {self.hotkey_name}"
        )

        # Initialize wallet
        self.wallet = self.load_wallet()

    def load_wallet(self) -> bt.wallet:
        """Load or create wallet based on environment variables.

        This method:
        1. Initializes subtensor connection
        2. Creates/loads the wallet
        3. Sets up coldkey from mnemonic if needed
        4. Sets up hotkey
        5. Handles registration if needed

        Returns:
            bt.wallet: The loaded and configured wallet

        Raises:
            Exception: If COLDKEY_MNEMONIC is not provided when needed
            Exception: If registration fails after retries
        """
        # Initialize subtensor - only specify network if it's test
        self.subtensor = (
            bt.subtensor(network="test") if self.network == "test" else bt.subtensor()
        )

        print("=== Wallet Setup ===")
        print(f"Using wallet: {self.wallet_name}")
        self.logger.info("Using wallet: %s", self.wallet_name)

        # First just load/create wallet without hotkey
        self.wallet = bt.wallet(name=self.wallet_name)

        # Check for coldkey and regenerate if needed
        coldkey_path = os.path.join(
            "/root/.bittensor/wallets", self.wallet_name, "coldkey"
        )
        if os.path.exists(coldkey_path):
            print(f"Found existing coldkey at {coldkey_path}")
            self.logger.info("Found existing coldkey at %s", coldkey_path)
        else:
            print(f"No coldkey found at {coldkey_path}")
            self.logger.info("No coldkey found at %s", coldkey_path)
            mnemonic = os.environ.get("COLDKEY_MNEMONIC")
            if not mnemonic:
                print("ERROR: COLDKEY_MNEMONIC environment variable is required")
                self.logger.error("COLDKEY_MNEMONIC environment variable is required")
                raise Exception("COLDKEY_MNEMONIC not provided")

            print("Attempting to regenerate coldkey from mnemonic...")
            self.logger.info("Attempting to regenerate coldkey from mnemonic")
            try:
                self.wallet.regenerate_coldkey(
                    mnemonic=mnemonic, use_password=False, overwrite=True
                )
                print("Successfully regenerated coldkey")
                self.logger.info("Successfully regenerated coldkey")
            except Exception as e:
                print(f"Failed to regenerate coldkey: {str(e)}")
                self.logger.error("Failed to regenerate coldkey: %s", str(e))
                raise

        # Now that we have a coldkey, set up the hotkey
        self.setup_hotkey()

        # Check registration status
        is_registered = self.subtensor.is_hotkey_registered(
            netuid=self.netuid,
            hotkey_ss58=self.wallet.hotkey.ss58_address,
        )

        if not is_registered:
            print(
                f"Hotkey {self.hotkey_name} is not registered, attempting registration..."
            )
            self.logger.info(
                "Hotkey %s is not registered, attempting registration...",
                self.hotkey_name,
            )
            uid = self.register()
            if uid is not None:
                print(
                    f"Successfully registered hotkey {self.hotkey_name} with UID {uid}"
                )
                self.logger.info(
                    "Successfully registered hotkey %s with UID %d",
                    self.hotkey_name,
                    uid,
                )
            else:
                print(f"Failed to register hotkey {self.hotkey_name}")
                self.logger.error("Failed to register hotkey %s", self.hotkey_name)
                raise Exception("Failed to register hotkey")
        else:
            uid = self.subtensor.get_uid_for_hotkey_on_subnet(
                hotkey_ss58=self.wallet.hotkey.ss58_address,
                netuid=self.netuid,
            )
            print(f"Hotkey {self.hotkey_name} is already registered with UID {uid}")
            self.logger.info(
                "Hotkey %s is already registered with UID %d", self.hotkey_name, uid
            )
            self.update_hotkey_mappings(uid)

        return self.wallet

    def get_wallet(self) -> bt.wallet:
        """Get the loaded wallet.

        Returns:
            Loaded wallet
        """
        return self.wallet

    def setup_hotkey(self):
        """Set up hotkey after coldkey is established.

        This method:
        1. Creates wallet with specific hotkey name
        2. Creates new hotkey if it doesn't exist
        3. Uses existing hotkey if found

        The hotkey path is: /root/.bittensor/wallets/{wallet_name}/hotkeys/{hotkey_name}
        """
        self.logger.info("Setting up hotkey %s", self.hotkey_name)

        # First create the wallet with the hotkey name we want and explicit path
        self.wallet = bt.wallet(
            name=self.wallet_name,
            hotkey=self.hotkey_name,
            path="/root/.bittensor/wallets/",
        )

        hotkey_path = os.path.join(
            "/root/.bittensor/wallets", self.wallet_name, "hotkeys", self.hotkey_name
        )
        if not os.path.exists(hotkey_path):
            self.logger.info("Creating new hotkey %s", self.hotkey_name)
            self.wallet.create_new_hotkey(use_password=False, overwrite=False)
        else:
            self.logger.info("Found existing hotkey %s", self.hotkey_name)

    def update_hotkey_mappings(self, uid: int):
        """Update hotkey mappings file with current hotkey info.

        Maintains a JSON file mapping hotkeys to their metadata including:
        - UID
        - Role
        - Network UID
        - Wallet name
        - Hotkey name

        Args:
            uid: UID assigned to the hotkey

        Note:
            File is stored at ./.bt-masa/hotkey_mappings.json
        """
        mappings_file = os.path.expanduser("./.bt-masa/hotkey_mappings.json")
        os.makedirs(os.path.dirname(mappings_file), mode=0o700, exist_ok=True)

        mappings = {}
        if os.path.exists(mappings_file):
            try:
                with open(mappings_file, "r") as f:
                    mappings = json.load(f)
            except json.JSONDecodeError:
                self.logger.warning(
                    "Could not parse existing mappings file, starting fresh"
                )

        mappings[self.wallet.hotkey.ss58_address] = {
            "uid": uid,
            "role": self.role,
            "netuid": self.netuid,
            "wallet_name": self.wallet.name,
            "hotkey_name": self.hotkey_name,
        }

    def register(self) -> Optional[int]:
        """Register wallet with subnet.

        Attempts registration with infinite retry on common errors:
        - Priority too low
        - Invalid transaction
        - Other substrate errors

        Returns:
            int: The assigned UID if registration successful
            None: If registration fails

        Note:
            This method will retry indefinitely until registration succeeds
        """
        self.logger.info("Starting registration for hotkey %s", self.hotkey_name)

        while True:
            try:
                # Attempt registration
                success = self.subtensor.burned_register(
                    wallet=self.wallet,
                    netuid=self.netuid,
                )

                if success:
                    # Get the UID after successful registration
                    uid = self.subtensor.get_uid_for_hotkey_on_subnet(
                        hotkey_ss58=self.wallet.hotkey.ss58_address,
                        netuid=self.netuid,
                    )
                    self.update_hotkey_mappings(uid)
                    print("\n=== REGISTRATION SUCCESSFUL ===")
                    print(f"Hotkey: {self.hotkey_name}")
                    print(f"UID: {uid}")
                    print(f"Network: {self.network}")
                    print(f"Netuid: {self.netuid}")
                    print("===============================\n")
                    return uid

                self.logger.warning(
                    "Registration attempt failed, retrying in 10 seconds..."
                )
                time.sleep(10)

            except SubstrateRequestException as e:
                error_msg = str(e)
                if "Priority is too low" in error_msg:
                    self.logger.warning(
                        "Registration queued, retrying in 10 seconds... (Priority is too low)"
                    )
                    time.sleep(10)
                elif "Invalid Transaction" in error_msg:
                    self.logger.warning(
                        "Registration blocked, retrying in 10 seconds... (Invalid Transaction)"
                    )
                    time.sleep(10)
                else:
                    self.logger.error(
                        "Unexpected registration error, retrying in 10 seconds..."
                    )
                    time.sleep(10)
            except Exception:
                self.logger.warning("Registration failed, retrying in 10 seconds...")
