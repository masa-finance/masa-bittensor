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

import os
import torch
import asyncio
import threading
import argparse

import bittensor as bt

from masa.base.neuron import BaseNeuron
from masa.utils.config import add_miner_args

from typing import Dict
from masa.synapses import PingAxonSynapse
from masa.base.healthcheck import handle_ping

from masa.miner.twitter.profile import handle_twitter_profile
from masa.miner.twitter.followers import handle_twitter_followers
from masa.miner.twitter.tweets import handle_recent_tweets, RecentTweetsSynapse


class BaseMinerNeuron(BaseNeuron):
    """
    Base class for Bittensor miners.
    """

    neuron_type: str = "MinerNeuron"

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        super().add_args(parser)
        add_miner_args(cls, parser)

    def __init__(self, config=None):

        self._is_initialized = False
        super().__init__(config=config)

        # Warn if allowing incoming requests from anyone.
        if not self.config.blacklist.force_validator_permit:
            bt.logging.warning(
                "You are allowing non-validators to send requests to your miner. This is a security risk."
            )
        if self.config.blacklist.allow_non_registered:
            bt.logging.warning(
                "You are allowing non-registered entities to send requests to your miner. This is a security risk."
            )

    async def initialize(self, config=None):
        """Async initialization method."""
        if self._is_initialized:
            return

        await super().initialize(config)

        subnet_params = await self.subtensor.get_subnet_hyperparameters(
            self.config.netuid
        )
        self.tempo = subnet_params.tempo
        self.axon = bt.axon(
            wallet=self.wallet, port=self.config.axon.port, config=self.config
        )

        # Attach determiners which functions are called when servicing a request.
        bt.logging.info("Attaching forward functions to miner axon...")

        self.axon.attach(forward_fn=self.handle_ping_wrapper)

        self.axon.attach(
            forward_fn=handle_twitter_profile,
            blacklist_fn=self.blacklist_twitter_profile,
            priority_fn=self.priority_twitter_profile,
        )

        self.axon.attach(
            forward_fn=handle_twitter_followers,
            blacklist_fn=self.blacklist_twitter_followers,
            priority_fn=self.priority_twitter_followers,
        )

        self.axon.attach(
            forward_fn=self.handle_recent_tweets_wrapper,
            blacklist_fn=self.blacklist_recent_tweets,
            priority_fn=self.priority_recent_tweets,
        )

        bt.logging.info(f"Axon created: {self.axon}")

        # Instantiate runners
        self.should_exit: bool = False
        self.is_running: bool = False
        self.thread: threading.Thread = None
        self.auto_update_thread: threading.Thread = None
        self.lock = asyncio.Lock()

        self.neurons_permit_stake: Dict[str, int] = (
            {}
        )  # dict of neurons (hotkeys) that meet min stake requirement with their respective last fetched block numbers
        self.min_stake_required: int = (
            self.config.blacklist.min_stake_required
        )  # note, this will be variable per environment

        self.load_state()

        # miners have to serve their axon
        await self.serve_axon()
        self.axon.start()
        self._is_initialized = True

    def handle_recent_tweets_wrapper(
        self, synapse: RecentTweetsSynapse
    ) -> RecentTweetsSynapse:
        return handle_recent_tweets(synapse, self.config.twitter.max_tweets_per_request)

    def handle_ping_wrapper(self, synapse: PingAxonSynapse) -> PingAxonSynapse:
        return handle_ping(synapse, self.spec_version)

    async def serve_axon(self):
        """Serve axon to enable external connections."""
        bt.logging.info("serving ip to chain...")

        try:
            await self.subtensor.serve_axon(
                netuid=self.config.netuid,
                axon=self.axon,
            )
            bt.logging.info(
                f"Running miner {self.axon} on network: {self.config.subtensor.chain_endpoint} with netuid: {self.config.netuid}"
            )
        except Exception as e:
            bt.logging.error(f"Failed to serve Axon with exception: {e}")

    async def run(self):
        """Run the miner forever."""
        while True:
            current_block = await self.block
            bt.logging.info(f"Syncing at block {current_block}")
            await self.sync()
            self.last_sync_block = current_block

    # note, runs every tempo
    async def run_auto_update(self):
        while not self.should_exit:
            try:
                if self.config.neuron.auto_update:
                    self.auto_update()
            except Exception as e:
                bt.logging.error(f"Error running auto update: {e}")
            await asyncio.sleep(self.tempo * 12)  # note, 12 seconds per block

    def run_auto_update_in_loop(self):
        asyncio.run(self.run_auto_update())

    async def sync(self):
        """
        Synchronizes the miner's state with the network.
        """
        await self.metagraph.sync(subtensor=self.subtensor)

    def save_state(self):
        """Saves the state of the miner to a file."""
        bt.logging.info("Saving miner state.")

        # Save the state of the miner to file.
        torch.save(
            {
                "neurons_permit_stake": self.neurons_permit_stake,
            },
            self.config.neuron.full_path + "/state.pt",
        )

    def load_state(self):
        """Loads the state of the miner from a file."""
        bt.logging.info("Loading miner state.")

        # Load the state of the miner from file.
        state_path = self.config.neuron.full_path + "/state.pt"
        if os.path.isfile(state_path):
            state = torch.load(state_path, map_location=torch.device("cpu"))
            self.neurons_permit_stake = dict(state).get("neurons_permit_stake", {})
        else:
            self.neurons_permit_stake = {}
            bt.logging.warning(
                f"State file not found at {state_path}. Skipping state load."
            )
