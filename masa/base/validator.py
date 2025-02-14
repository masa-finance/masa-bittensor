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

    async def should_set_weights(self) -> bool:
        # Don't set weights on initialization or if disabled
        if self.step == 0 or self.config.neuron.disable_set_weights:
            bt.logging.debug("Weight setting disabled: initialization or config")
            return False

        # Check if enough epoch blocks have elapsed
        blocks_elapsed = await self.block - self.metagraph.last_update[self.uid]
        if blocks_elapsed <= self.config.neuron.epoch_length:
            return False

        # Count how many miners we have scores for
        non_zero_scores = (self.scores > 0).sum().item()
        total_miners = len(self.metagraph.hotkeys)
        score_coverage = non_zero_scores / total_miners if total_miners > 0 else 0

        # We want at least 80% of miners to have scores before setting weights
        MIN_COVERAGE = 0.8
        if score_coverage < MIN_COVERAGE:
            bt.logging.info(
                f"Not enough miner coverage for weight setting: {non_zero_scores}/{total_miners} miners scored ({score_coverage:.1%})"
            )
            return False

        bt.logging.info(
            f"Should set weights: {blocks_elapsed} blocks elapsed > {self.config.neuron.epoch_length} epoch length "
            f"with {non_zero_scores}/{total_miners} miners scored ({score_coverage:.1%})"
        )
        return True

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
        bt.logging.info(f"Normalized weights sum: {weights.sum()}")

        # Convert to chain format
        uint_uids, uint_weights = (
            bt.utils.weight_utils.convert_weights_and_uids_for_emit(
                uids=self.metagraph.uids,
                weights=weights.to("cpu").numpy(),
            )
        )

        # Create weight entry in the exact format needed
        import datetime
        import json

        # Convert weights to the format in scores.log
        weights_list = [
            {"uid": int(uid), "weight": float(weight * 65535)}  # Scale to u16::MAX
            for uid, weight in zip(uint_uids, uint_weights)
        ]

        log_entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            "netuid": self.config.netuid,
            "hotkey": self.wallet.hotkey.ss58_address,
            "weights": weights_list,
        }

        # Log to scores.log
        log_file = os.path.join(self.config.neuron.full_path, "scores.log")
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
            bt.logging.info(f"Logged weights for {len(uint_uids)} uids to {log_file}")
            bt.logging.debug(
                f"Weight stats - Min: {weights.min():.6f}, Max: {weights.max():.6f}, Mean: {weights.mean():.6f}"
            )
        except Exception as e:
            bt.logging.error(f"Failed to log weights: {e}")

        # NOTE: Weight setting on chain disabled for now while we analyze scoring
        # try:
        #     # Set weights on chain (standard bittensor approach)
        #     result = await self.subtensor.set_weights(
        #         netuid = self.config.netuid,
        #         wallet = self.wallet,
        #         uids = uint_uids,
        #         weights = uint_weights,
        #         version_key = self.spec_version,
        #         wait_for_inclusion = False,
        #         wait_for_finalization = False,
        #     )
        #     if result:
        #         bt.logging.success(f"Successfully set weights on chain for {len(uint_uids)} uids")
        #     else:
        #         bt.logging.error("Failed to set weights on chain")
        # except Exception as e:
        #     bt.logging.error(f"Failed to set weights on chain with error: {e}")

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

        # Ensure scores tensor is large enough for the current metagraph
        if len(self.scores) < self.metagraph.n:
            bt.logging.info(
                f"Expanding scores tensor to match metagraph size: {self.metagraph.n}"
            )
            new_scores = torch.zeros(self.metagraph.n, dtype=torch.float32).to(
                self.device
            )
            new_scores[: len(self.scores)] = self.scores
            self.scores = new_scores

        # Zero out all hotkeys that have been replaced.
        for uid, hotkey in enumerate(self.hotkeys):
            if (
                uid < len(self.metagraph.hotkeys)
                and hotkey != self.metagraph.hotkeys[uid]
            ):
                self.scores[uid] = 0  # hotkey has been replaced
                # Take the last 6 objects in the self.volumes list
                recent_volumes = self.volumes[-self.volume_window :]
                # Replace all instances of miners[uid] and set their values to 0
                for volume in recent_volumes:
                    if str(uid) in volume["miners"]:
                        volume["miners"][str(uid)] = 0

                # Replace unique tweets by uid
                self.tweets_by_uid[uid] = set()

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
        try:
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
                raise ValueError(
                    "The length of uids_tensor and rewards must be the same."
                )

            # Get the maximum UID value needed
            max_uid_needed = max(max(uids), self.metagraph.n - 1)
            current_size = len(self.scores)

            bt.logging.debug(
                f"Current scores size: {current_size}, Max UID needed: {max_uid_needed}"
            )

            # If we need to expand the scores tensor
            if max_uid_needed >= current_size:
                new_size = max(max_uid_needed + 1, self.metagraph.n)
                bt.logging.info(
                    f"Expanding scores tensor from size {current_size} to {new_size}"
                )
                new_scores = torch.zeros(new_size, dtype=torch.float32).to(self.device)
                new_scores[:current_size] = self.scores
                self.scores = new_scores

            # Create a zero tensor for scattered rewards with the same size as scores
            scattered_rewards = torch.zeros_like(self.scores)

            # Scatter the rewards into the zero tensor
            scattered_rewards.scatter_(0, uids_tensor, rewards)

            bt.logging.debug(
                f"Scattered rewards shape: {scattered_rewards.shape}, Scores shape: {self.scores.shape}"
            )
            bt.logging.info(f"Scattered rewards: {rewards}")

            # Update scores with rewards produced by this step.
            alpha: float = self.config.neuron.moving_average_alpha
            self.scores = alpha * scattered_rewards + (1 - alpha) * self.scores

            bt.logging.info(f"Updated moving averages: {self.scores}")

            # Limit the number of tweet IDs stored per UID to 100,000
            for uid in uids:
                if uid not in self.tweets_by_uid:
                    self.tweets_by_uid[uid] = set()
                elif len(self.tweets_by_uid[uid]) > 100000:
                    self.tweets_by_uid[uid] = set(
                        list(self.tweets_by_uid[uid])[:100000]
                    )

            self.save_state()

        except Exception as e:
            bt.logging.error(f"Error in update_scores: {str(e)}")
            bt.logging.debug(
                f"Debug info - UIDs: {uids}, Rewards shape: {rewards.shape}, Scores shape: {self.scores.shape}, Metagraph size: {self.metagraph.n}"
            )
            raise

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
        """Loads the state of the validator from a file and rebuilds scores from scores.log if needed."""
        bt.logging.info("Loading validator state.")

        # Load the state of the validator from file
        state_path = self.config.neuron.full_path + "/state.pt"
        scores_log_path = os.path.join(self.config.neuron.full_path, "scores.log")

        if os.path.isfile(state_path):
            state = torch.load(state_path, map_location=torch.device("cpu"))
            self.step = dict(state).get("step", 0)
            self.scores = dict(state).get("scores", torch.zeros(self.metagraph.n))
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
                f"State file not found at {state_path}. Attempting to rebuild from scores.log"
            )

        # If we have no scores or very few non-zero scores, try to rebuild from scores.log
        non_zero_scores = (self.scores > 0).sum().item()
        if (
            os.path.isfile(scores_log_path)
            and non_zero_scores < len(self.metagraph.hotkeys) * 0.5
        ):
            bt.logging.info(f"Attempting to rebuild scores from {scores_log_path}")
            try:
                with open(scores_log_path, "r") as f:
                    # Read the last line of scores.log
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            if entry["netuid"] == self.config.netuid:
                                last_weights = entry["weights"]
                                # Convert weights back to scores (undo the u16::MAX scaling)
                                new_scores = torch.zeros(self.metagraph.n)
                                for weight in last_weights:
                                    uid = weight["uid"]
                                    if uid < len(new_scores):
                                        new_scores[uid] = weight["weight"] / 65535.0

                                if (new_scores > 0).sum().item() > non_zero_scores:
                                    bt.logging.info(
                                        f"Rebuilt scores from scores.log with {(new_scores > 0).sum().item()} non-zero scores"
                                    )
                                    self.scores = new_scores
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                bt.logging.error(f"Failed to rebuild scores from scores.log: {e}")

        bt.logging.info(
            f"Loaded state with {(self.scores > 0).sum().item()}/{len(self.scores)} non-zero scores"
        )
