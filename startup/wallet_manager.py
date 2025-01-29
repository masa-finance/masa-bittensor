import os
import logging
import json
import bittensor as bt
from contextlib import redirect_stdout


class WalletManager:
    """Manages wallet operations including creation, initialization, and mapping updates."""

    def __init__(self, wallet_name: str, hotkey: str, netuid: int, network: str):
        """Initialize the wallet manager.

        Args:
            wallet_name: Name of the wallet
            hotkey: Hotkey name
            netuid: Network UID
            network: Network name (e.g., 'test', 'main')
        """
        self.wallet_name = wallet_name
        self.hotkey = hotkey
        self.netuid = netuid
        self.network = network
        self.logger = logging.getLogger(__name__)

    def setup_wallet_directories(self):
        """Create wallet directories with proper permissions."""
        wallet_dir = os.path.expanduser(f"~/.bittensor/wallets/{self.wallet_name}")
        os.makedirs(wallet_dir, mode=0o700, exist_ok=True)
        os.makedirs(os.path.join(wallet_dir, "hotkeys"), mode=0o700, exist_ok=True)

    def initialize_wallet(
        self, coldkey_mnemonic: str = None, is_validator: bool = False
    ):
        """Initialize wallet with coldkey and hotkey.

        Args:
            coldkey_mnemonic: Optional mnemonic for coldkey regeneration
            is_validator: Whether this is a validator wallet

        Returns:
            bt.wallet: Initialized wallet object
        """
        wallet = bt.wallet(
            name=self.wallet_name,
            hotkey=self.hotkey,
            path=os.path.expanduser("~/.bittensor/wallets/"),
        )

        # Handle coldkey
        coldkey_path = os.path.join(wallet.path, self.wallet_name, "coldkey")
        if not os.path.exists(coldkey_path):
            if is_validator and not coldkey_mnemonic:
                raise Exception(
                    "No coldkey found and COLDKEY_MNEMONIC not provided for validator"
                )
            if coldkey_mnemonic:
                self._regenerate_coldkey(wallet, coldkey_mnemonic)

        # Handle hotkey
        hotkey_path = os.path.join(
            wallet.path, self.wallet_name, "hotkeys", self.hotkey
        )
        if not os.path.exists(hotkey_path):
            self._create_hotkey(wallet)

        return wallet

    def _regenerate_coldkey(self, wallet, mnemonic):
        """Regenerate coldkey from mnemonic."""
        self.logger.info("Regenerating coldkey from mnemonic")
        with open(os.devnull, "w") as devnull:
            with redirect_stdout(devnull):
                try:
                    wallet.regenerate_coldkey(
                        mnemonic=mnemonic,
                        use_password=False,
                        overwrite=False,
                    )
                except Exception as e:
                    if "already exists" in str(e):
                        self.logger.info(
                            "Coldkey already exists, skipping regeneration"
                        )
                    else:
                        raise

    def _create_hotkey(self, wallet):
        """Create new hotkey."""
        self.logger.info(f"Creating new hotkey {self.hotkey}")
        with open(os.devnull, "w") as devnull:
            with redirect_stdout(devnull):
                try:
                    wallet.create_new_hotkey(
                        use_password=False,
                        overwrite=False,
                    )
                except Exception as e:
                    if "already exists" in str(e):
                        self.logger.info("Hotkey already exists, skipping creation")
                    else:
                        raise

    def update_hotkey_mappings(self, wallet, uid: int, role: str):
        """Update hotkey mappings file with current hotkey info.

        Args:
            wallet: Initialized wallet object
            uid: UID assigned to the hotkey
            role: Role of the node (validator/miner)
        """
        mappings_file = os.path.expanduser("~/.bt-masa/hotkey_mappings.json")
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

        mappings[wallet.hotkey.ss58_address] = {
            "uid": uid,
            "role": role,
            "netuid": self.netuid,
            "wallet_name": self.wallet_name,
            "hotkey_name": self.hotkey,
        }

        with open(mappings_file, "w") as f:
            json.dump(mappings, f, indent=2)
        self.logger.info("Updated hotkey mappings in %s", mappings_file)
