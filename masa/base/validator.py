# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Masa

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
import copy
import torch
import json
import asyncio
import aiohttp
import argparse
import bittensor as bt

from typing import List

from masa.base.neuron import BaseNeuron
from masa.utils.config import add_validator_args

from masa.validator.scorer import Scorer
from masa.validator.forwarder import Forwarder

from masa.utils.weights import process_weights_for_netuid


class BaseValidatorNeuron(BaseNeuron):
    """
    Base class for Bittensor validators. Your validator should inherit from this class.
    """

    neuron_type: str = "ValidatorNeuron"

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        super().add_args(parser)
        add_validator_args(cls, parser)

    def __init__(self, config=None):
        self.versions = []
        self.keywords = []
        self.uncalled_uids = set()
        self.volume_window = 6
        self.tweets_by_uid = {}
        self.volumes = []
        self._is_initialized = False
        super().__init__(config=config)

    async def run(self):
        """Run the validator forever."""
        while True:
            current_block = await self.block

            if current_block - self.last_sync_block > self.tempo:
                bt.logging.info(f"Syncing at block {current_block}")
                await self.sync()
                self.last_sync_block = current_block

            if current_block - self.last_tempo_block > self.tempo:
                bt.logging.info(f"Pinging miners at block {current_block}")
                await self.forwarder.ping_axons(current_block)
                self.last_tempo_block = current_block

            if current_block - self.last_volume_block > self.tempo:
                bt.logging.info(f"Getting miner volumes at block {current_block}")
                await self.forwarder.get_miners_volumes(current_block)
                self.last_volume_block = current_block

            if current_block - self.last_scoring_block > self.tempo:
                bt.logging.info(f"Scoring miner volumes at block {current_block}")
                await self.scorer.score_miner_volumes()
                self.last_scoring_block = current_block

            if current_block - self.last_healthcheck_block > self.tempo:
                bt.logging.info(f"Running health check at block {current_block}")
                await self.healthcheck()
                self.last_healthcheck_block = current_block

            await asyncio.sleep(1)

    async def initialize(self, config=None):
        """Async initialization method."""
        if self._is_initialized:
            return

        # Initialize parent class async components
        await super().initialize(config)

        self.forwarder = Forwarder(self)
        self.scorer = Scorer(self)

        self.hotkeys = copy.deepcopy(self.metagraph.hotkeys)
        subnet_params = await self.subtensor.get_subnet_hyperparameters(
            self.config.netuid
        )
        self.tempo = subnet_params.tempo
        self.block_time = 12

        self.last_sync_block = 0
        self.last_tempo_block = 0
        self.last_volume_block = 0
        self.last_scoring_block = 0
        self.last_healthcheck_block = 0

        # load config file for subnet specific settings as default
        # note, every tempo we fetch the latest config file from github main branch
        with open("config.json", "r") as config_file:
            config = json.load(config_file)
            network = (
                "testnet" if self.config.subtensor.network == "test" else "mainnet"
            )
            subnet_config = config.get(network, {})
            bt.logging.info(f"Loaded subnet config: {subnet_config}")
            self.subnet_config = subnet_config

        self.dendrite = bt.dendrite(wallet=self.wallet)
        self.scores = torch.zeros(
            self.metagraph.n, dtype=torch.float32, device=self.device
        )
        # Init sync with the network. Updates the metagraph.
        await self.sync()
        self.load_state()

        # Serve axon to enable external connections.
        if not self.config.neuron.axon_off:
            await self.serve_axon()
        else:
            bt.logging.warning("axon off, not serving ip to chain.")

        self._is_initialized = True

    async def serve_axon(self):
        """Serve axon to enable external connections."""
        bt.logging.info("serving ip to chain...")
        try:
            self.axon = bt.axon(
                wallet=self.wallet, config=self.config, port=self.config.axon.port
            )

            try:
                await self.subtensor.serve_axon(
                    netuid=self.config.netuid,
                    axon=self.axon,
                )
                bt.logging.info(
                    f"Running validator {self.axon} on network: {self.config.subtensor.chain_endpoint} with netuid: {self.config.netuid}"
                )
            except Exception as e:
                bt.logging.error(f"Failed to serve Axon with exception: {e}")

        except Exception as e:
            bt.logging.error(f"Failed to create Axon initialize with exception: {e}")

    async def healthcheck(self):
        """Run health check and auto-update."""
        try:
            # Fetch latest config from GitHub
            await self.update_config()

            # Run any other health checks here
            pass
        except Exception as e:
            bt.logging.error(f"Error in health check: {e}")

    async def update_config(self):
        """Update config from GitHub."""
        try:
            # Implement config update logic here
            pass
        except Exception as e:
            bt.logging.error(f"Error updating config: {e}")

    async def set_weights(self):
        """Logs the weights we would set based on miner scores."""
        # Skip if we have no real scores yet
        if torch.all(self.scores == 0):
            bt.logging.info("No real scores yet, skipping weight setting")
            return

        if torch.isnan(self.scores).any():
            bt.logging.warning(
                "Scores contain NaN values. This may be due to a lack of responses from miners, or a bug in your reward functions."
            )
            return

        # Normalize scores to weights
        weights = torch.nn.functional.normalize(self.scores, p=1, dim=0)

        # Convert to chain format
        uint_uids, uint_weights = (
            bt.utils.weight_utils.convert_weights_and_uids_for_emit(
                uids=self.metagraph.uids,
                weights=weights.to("cpu").numpy(),
            )
        )

        # Create a log entry with timestamp
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "uids": uint_uids.tolist(),
            "weights": uint_weights.tolist(),
        }

        # Log to file
        import json
        import os

        log_file = os.path.join(self.config.neuron.full_path, "weight_logs.json")

        try:
            # Read existing logs if file exists
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    logs = json.load(f)
            else:
                logs = []

            # Append new log
            logs.append(log_entry)

            # Write back to file
            with open(log_file, "w") as f:
                json.dump(logs, f, indent=2)

            bt.logging.info(f"Logged weights for {len(uint_uids)} uids to {log_file}")

        except Exception as e:
            bt.logging.error(f"Failed to log weights: {e}")

        # NOTE: Weight setting on chain disabled for now while we analyze scoring
        # result = await self.subtensor.set_weights(
        #     wallet=self.wallet,
        #     netuid=self.config.netuid,
        #     uids=uint_uids,
        #     weights=uint_weights,
        #     wait_for_finalization=False,
        #     wait_for_inclusion=False,
        #     version_key=self.spec_version,
        # )

    async def resync_metagraph(self):
        """Resyncs the metagraph and updates the hotkeys and moving averages based on the new metagraph."""
        bt.logging.info("resync_metagraph()")

        # Copies state of metagraph before syncing.
        previous_metagraph = copy.deepcopy(self.metagraph)

        # Sync the metagraph.
        await self.metagraph.sync(subtensor=self.subtensor)

        # Check if the metagraph axon info has changed.
        if previous_metagraph.axons == self.metagraph.axons:
            return

        bt.logging.info(
            "Metagraph updated, re-syncing hotkeys, dendrite pool and moving averages"
        )
        # Zero out all hotkeys that have been replaced.
        for uid, hotkey in enumerate(self.hotkeys):
            if hotkey != self.metagraph.hotkeys[uid]:
                self.scores[uid] = 0  # hotkey has been replaced
                # Take the last 6 objects in the self.volumes list
                recent_volumes = self.volumes[-self.volume_window :]
                # Replace all instances of miners[uid] and set their values to 0
                for volume in recent_volumes:
                    if str(uid) in volume["miners"]:
                        volume["miners"][str(uid)] = 0

                # Replace unique tweets by uid
                self.tweets_by_uid[uid] = set()

        # Check to see if the metagraph has changed size.
        # If so, we need to add new hotkeys and moving averages.
        if len(self.hotkeys) < len(self.metagraph.hotkeys):
            # Update the size of the moving average scores.
            new_moving_average = torch.zeros((self.metagraph.n)).to(self.device)
            min_len = min(len(self.hotkeys), len(self.scores))
            new_moving_average[:min_len] = self.scores[:min_len]
            self.scores = new_moving_average

        # Update the hotkeys.
        self.hotkeys = copy.deepcopy(self.metagraph.hotkeys)

    async def export_tweets(self, tweets: List[dict], query: str):
        """Exports tweets to a specified API in chunks of 1000."""
        api_url = self.config.validator.export_url
        if api_url:
            try:
                async with aiohttp.ClientSession() as session:
                    for i in range(0, len(tweets), 1000):
                        chunk = tweets[i : i + 1000]
                        payload = {
                            "Hotkey": self.wallet.hotkey.ss58_address,
                            "Query": query,
                            "Tweets": chunk,
                        }
                        async with session.post(api_url, json=payload) as response:
                            if response.status == 200:
                                bt.logging.success(
                                    f"Successfully sent data to the protocol API for chunk starting at index {i}."
                                )
                            else:
                                bt.logging.error(
                                    f"Failed to send data to the protocol API for chunk starting at index {i}: {response.status}"
                                )
                        await asyncio.sleep(1)  # Wait for 1 second between requests
            except Exception as e:
                bt.logging.error(
                    f"Exception occurred while sending data to the protocol API: {e}"
                )
        else:
            bt.logging.warning(
                "Tweets not exported, missing config --validator.export_url"
            )

    def update_scores(self, rewards: torch.FloatTensor, uids: List[int]):
        """Performs exponential moving average on the scores based on the rewards received from the miners."""

        # Check if rewards contains NaN values.
        if torch.isnan(rewards).any():
            bt.logging.warning(f"NaN values detected in rewards: {rewards}")
            # Replace any NaN values in rewards with 0.
            rewards = torch.nan_to_num(rewards, 0)

        # Check if `uids` is already a tensor and clone it to avoid the warning.
        if isinstance(uids, torch.Tensor):
            uids_tensor = uids.clone().detach()
        else:
            uids_tensor = torch.tensor(uids).to(self.device)

        # Ensure that the uids_tensor and rewards have the same length
        if len(uids_tensor) != len(rewards):
            raise ValueError("The length of uids_tensor and rewards must be the same.")

        # Ensure self.scores has the required length to accommodate all uids in uids_tensor
        max_uid = uids_tensor.max().item()
        if max_uid >= self.scores.size(0):
            new_size = max_uid + 1
            new_scores = torch.zeros(new_size).to(self.device)
            new_scores[: self.scores.size(0)] = self.scores
            self.scores = new_scores

        # Compute forward pass rewards, assumes uids are mutually exclusive.
        # shape: [ metagraph.n ]
        scattered_rewards: torch.FloatTensor = self.scores.scatter(
            0, uids_tensor, rewards
        ).to(self.device)

        bt.logging.info(f"Scattered rewards: {rewards}")

        # Update scores with rewards produced by this step.
        # shape: [ metagraph.n ]

        alpha: float = self.config.neuron.moving_average_alpha
        self.scores: torch.FloatTensor = alpha * scattered_rewards + (
            1 - alpha
        ) * self.scores.to(self.device)

        bt.logging.info(f"Updated moving averages: {self.scores}")

        # Limit the number of tweet IDs stored per UID to 100,000
        for uid in uids:
            if len(self.tweets_by_uid[uid]) > 100000:
                self.tweets_by_uid[uid] = set(list(self.tweets_by_uid[uid])[:100000])

        self.save_state()

    def save_state(self):
        """Saves the state of the validator to a file."""
        bt.logging.info("Saving validator state.")

        # Save the state of the validator to file.
        torch.save(
            {
                "step": self.step,
                "scores": self.scores,
                "hotkeys": self.hotkeys,
                "volumes": self.volumes,
                # "tweets_by_uid": self.tweets_by_uid,
            },
            self.config.neuron.full_path + "/state.pt",
        )

    def load_state(self):
        """Loads the state of the validator from a file."""
        bt.logging.info("Loading validator state.")

        # Load the state of the validator from file.
        state_path = self.config.neuron.full_path + "/state.pt"
        if os.path.isfile(state_path):
            state = torch.load(state_path, map_location=torch.device("cpu"))
            self.step = dict(state).get("step", 0)
            self.scores = dict(state).get("scores", [])
            self.hotkeys = dict(state).get("hotkeys", [])
            self.volumes = dict(state).get("volumes", [])
            self.tweets_by_uid = dict(state).get("tweets_by_uid", {})
        else:
            self.step = 0
            self.scores = torch.zeros(self.metagraph.n)
            self.hotkeys = []
            self.volumes = []
            self.tweets_by_uid = {}
            bt.logging.warning(
                f"State file not found at {state_path}. Skipping state load."
            )
