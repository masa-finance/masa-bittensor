"""Wallet Manager Module for Agent Arena subnet."""

import logging
import os
import bittensor as bt
import time
from substrateinterface.exceptions import SubstrateRequestException
from typing import Optional

logger = logging.getLogger(__name__)


class WalletManager:
    """Manages wallet operations for validators and miners."""

    def __init__(self, role: str, network: str, netuid: int):
        self.role = role
        self.network = network
        self.netuid = netuid
        self.logger = logging.getLogger(__name__)
        self.subtensor = None

        self.wallet_name = os.environ.get("WALLET_NAME")
        self.hotkey_name = os.environ.get("HOTKEY_NAME")

        if not self.wallet_name or not self.hotkey_name:
            raise ValueError(
                "WALLET_NAME and HOTKEY_NAME environment variables must be set"
            )

        self.logger.info(
            f"Using wallet: {self.wallet_name}, hotkey: {self.hotkey_name}"
        )

        self.wallet = self.load_wallet()

    def load_wallet(self) -> bt.wallet:
        """Load or create wallet and handle registration if needed."""
        self.subtensor = (
            bt.subtensor(network="test") if self.network == "test" else bt.subtensor()
        )

        print("=== Wallet Setup ===")
        print(f"Using wallet: {self.wallet_name}")
        self.logger.info("Using wallet: %s", self.wallet_name)

        self.wallet = bt.wallet(name=self.wallet_name)

        coldkey_path = os.path.join(
            "/root/.bittensor/wallets", self.wallet_name, "coldkey"
        )
        if not os.path.exists(coldkey_path):
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

        self.setup_hotkey()

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

        return self.wallet

    def get_wallet(self) -> bt.wallet:
        """Return the loaded wallet."""
        return self.wallet

    def setup_hotkey(self):
        """Set up or load existing hotkey."""
        self.logger.info("Setting up hotkey %s", self.hotkey_name)

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

    def register(self) -> Optional[int]:
        """Register wallet with subnet and return UID if successful."""
        self.logger.info("Starting registration for hotkey %s", self.hotkey_name)

        while True:
            try:
                success = self.subtensor.burned_register(
                    wallet=self.wallet,
                    netuid=self.netuid,
                )

                if success:
                    uid = self.subtensor.get_uid_for_hotkey_on_subnet(
                        hotkey_ss58=self.wallet.hotkey.ss58_address,
                        netuid=self.netuid,
                    )
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
