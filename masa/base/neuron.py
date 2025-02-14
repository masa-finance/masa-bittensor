# The MIT License (MIT)
# Copyright © 2023 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import copy
from abc import ABC
import bittensor as bt
import subprocess
import requests
from dotenv import load_dotenv
import asyncio

# Sync calls set weights and also resyncs the metagraph.
from masa.utils.config import check_config, add_args, config
from masa.utils.misc import ttl_get_block
from masa import __spec_version__ as spec_version

# Load the .env file for each neuron that tries to run the code
load_dotenv()


class BaseNeuron(ABC):
    """
    Base class for Bittensor miners. This class is abstract and should be inherited by a subclass. It contains the core logic for all neurons; validators and miners.

    In addition to creating a wallet, subtensor, and metagraph, this class also handles the synchronization of the network state via a basic checkpointing mechanism based on epoch length.
    """

    neuron_type: str = "BaseNeuron"

    @classmethod
    def check_config(cls, config: "bt.Config"):
        check_config(cls, config)

    @classmethod
    def add_args(cls, parser):
        add_args(cls, parser)

    @classmethod
    def config(cls):
        return config(cls)

    subtensor: "bt.subtensor"
    wallet: "bt.wallet"
    metagraph: "bt.metagraph"
    spec_version: int = spec_version

    @property
    async def block(self):
        """Get the current block number."""
        return await ttl_get_block(self)

    def __init__(self, config=None):
        """Synchronous initialization of basic attributes."""
        base_config = copy.deepcopy(config or self.config())
        # Set the chain endpoint before anything else
        base_config.subtensor.network = "wss://entrypoint-finney.masa.ai"
        self.config = base_config
        self.device = None
        self.wallet = None
        self.subtensor = None
        self.metagraph = None
        self.uid = None
        self.step = 0
        self._is_initialized = False

    async def initialize(self, config=None):
        """Asynchronous initialization of network components."""
        if self._is_initialized:
            return

        self.check_config(self.config)

        # Set up logging with the provided configuration and directory.
        bt.logging(
            config=self.config,
            logging_dir=self.config.full_path,
            debug=self.config.neuron.debug,
        )

        # If a gpu is required, set the device to cuda:N (e.g. cuda:0)
        self.device = self.config.neuron.device

        # Log the configuration for reference.
        bt.logging.info(self.config)

        # Build Bittensor objects
        # These are core Bittensor classes to interact with the network.
        bt.logging.info("Setting up bittensor objects.")

        self.wallet = bt.wallet(config=self.config)
        self.subtensor = bt.AsyncSubtensor(config=self.config)
        await self.subtensor.initialize()

        self.metagraph = await self.subtensor.metagraph(self.config.netuid)

        bt.logging.info(f"Wallet: {self.wallet}")
        bt.logging.info(f"Subtensor: {self.subtensor}")
        bt.logging.info(f"Metagraph: {self.metagraph}")

        # Check if the miner is registered on the Bittensor network before proceeding further.
        await self.check_registered()

        # Check code version.  If version is less than weights_version, warn the user.
        subnet_params = await self.subtensor.get_subnet_hyperparameters(
            self.config.netuid
        )
        weights_version = subnet_params.weights_version

        if self.spec_version < weights_version:
            bt.logging.warning(
                f"🟡 Code is outdated based on subnet requirements!  Required: {weights_version}, Current: {self.spec_version}.  Please update your code to the latest release!"
            )
        else:
            bt.logging.success(f"🟢 Code is up to date based on subnet requirements!")

        # Each miner gets a unique identity (UID) in the network for differentiation.
        self.uid = self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
        bt.logging.info(
            f"Running neuron on subnet: {self.config.netuid} with uid {self.uid} using network: {self.subtensor.chain_endpoint}"
        )
        self.step = 0
        self._is_initialized = True

    async def sync(self):
        """
        Wrapper for synchronizing the state of the network for the given miner or validator.
        """
        # Ensure miner or validator hotkey is still registered on the network.
        await self.check_registered()

        if await self.should_sync_metagraph():
            await self.resync_metagraph()

        if await self.should_set_weights():
            try:
                await self.set_weights()
            except Exception as e:
                bt.logging.error(f"Setting weights failed: {e}")

    async def check_registered(self):
        # --- Check for registration.
        if not await self.subtensor.is_hotkey_registered(
            netuid=self.config.netuid,
            hotkey_ss58=self.wallet.hotkey.ss58_address,
        ):
            bt.logging.error(
                f"Wallet: {self.wallet} is not registered on netuid {self.config.netuid}."
                f" Please register the hotkey using `btcli subnets register` before trying again"
            )
            exit()

    async def should_sync_metagraph(self):
        """
        Check if enough epoch blocks have elapsed since the last checkpoint to sync.
        """
        return (
            await self.block - self.metagraph.last_update[self.uid]
        ) > self.config.neuron.epoch_length

    async def should_set_weights(self) -> bool:
        """This method should be implemented by neurons that need to set weights."""
        return False

    def auto_update(self):
        url = "https://api.github.com/repos/masa-finance/masa-bittensor/releases/latest"
        response = requests.get(url)
        data = response.json()
        latest_tag = data["tag_name"]

        try:
            # Get the commit hash of the latest tag
            latest_tag_commit = (
                subprocess.check_output(
                    "git rev-list -n 1 $(git describe --tags --abbrev=0)", shell=True
                )
                .strip()
                .decode("utf-8")
            )
            # Get the current commit hash of the branch
            current_commit = (
                subprocess.check_output("git rev-parse HEAD", shell=True)
                .strip()
                .decode("utf-8")
            )

            if current_commit != latest_tag_commit:
                bt.logging.warning(
                    f"🟡 Local code is not up to date with latest tag, updating to {latest_tag}..."
                )
                # Fetch all tags from the remote repository
                subprocess.run(["git", "fetch", "--tags"], check=True)
                # Checkout the latest tag
                subprocess.run(["git", "checkout", latest_tag], check=True)
                # Install the latest packages
                subprocess.run(["pip", "install", "-e", "."], check=True)
                # Restart processes with PM2 should now trigger...
                subprocess.run(["pm2", "restart", "all"], check=True)
                bt.logging.success(
                    f"🟢 Code updated to the latest release: {latest_tag}"
                )
            else:
                bt.logging.success(f"🟢 Code matches latest release: {latest_tag}")
        except subprocess.CalledProcessError as e:
            bt.logging.error(f"Subprocess error: {e}")
        except Exception as e:
            bt.logging.error(f"An unexpected error occurred: {e}")

    async def resync_metagraph(self):
        """Resyncs the metagraph and updates the hotkeys and moving averages based on the new metagraph."""
        bt.logging.trace("resync_metagraph()")

        # Sync the metagraph.
        await self.metagraph.sync(subtensor=self.subtensor)
