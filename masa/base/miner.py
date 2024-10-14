# The MIT License (MIT)
# Copyright © 2023 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import os
import time
import torch
import asyncio
import threading
import argparse
import traceback

import bittensor as bt

from masa.base.neuron import BaseNeuron
from masa.utils.config import add_miner_args

from typing import Dict
from masa.base.healthcheck import forward_ping, PingAxonSynapse

from masa.miner.twitter.profile import forward_twitter_profile
from masa.miner.twitter.followers import forward_twitter_followers
from masa.miner.twitter.tweets import forward_recent_tweets


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

        self.tempo = self.subtensor.get_subnet_hyperparameters(self.config.netuid).tempo

        # The axon handles request processing, allowing validators to send this miner requests.
        self.axon = bt.axon(
            wallet=self.wallet, port=self.config.axon.port, config=self.config
        )

        # Attach determiners which functions are called when servicing a request.
        bt.logging.info("Attaching forward functions to miner axon.")

        self.axon.attach(forward_fn=self.forward_ping_synapse)

        self.axon.attach(
            forward_fn=forward_twitter_profile,
            blacklist_fn=self.blacklist_twitter_profile,
            priority_fn=self.priority_twitter_profile,
        )

        self.axon.attach(
            forward_fn=forward_twitter_followers,
            blacklist_fn=self.blacklist_twitter_followers,
            priority_fn=self.priority_twitter_followers,
        )

        self.axon.attach(
            forward_fn=forward_recent_tweets,
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

    def forward_ping_synapse(self, synapse: PingAxonSynapse) -> PingAxonSynapse:
        return forward_ping(synapse, self.spec_version)

    def run(self):
        """
        Initiates and manages the main loop for the miner on the Bittensor network. The main loop handles graceful shutdown on keyboard interrupts and logs unforeseen errors.

        This function performs the following primary tasks:
        1. Check for registration on the Bittensor network.
        2. Starts the miner's axon, making it active on the network.
        3. Periodically resynchronizes with the chain; updating the metagraph with the latest network state and setting weights.

        The miner continues its operations until `should_exit` is set to True or an external interruption occurs.
        During each epoch of its operation, the miner waits for new blocks on the Bittensor network, updates its
        knowledge of the network (metagraph), and sets its weights. This process ensures the miner remains active
        and up-to-date with the network's latest state.

        Note:
            - The function leverages the global configurations set during the initialization of the miner.
            - The miner's axon serves as its interface to the Bittensor network, handling incoming and outgoing requests.

        Raises:
            KeyboardInterrupt: If the miner is stopped by a manual interruption.
            Exception: For unforeseen errors during the miner's operation, which are logged for diagnosis.
        """

        # Check that miner is registered on the network.
        self.sync()

        # Serve passes the axon information to the network + netuid we are hosting on.
        # This will auto-update if the axon port of external ip have changed.
        bt.logging.info(
            f"Serving miner axon {self.axon} on network: {self.config.subtensor.chain_endpoint} with netuid: {self.config.netuid}"
        )
        self.axon.serve(netuid=self.config.netuid, subtensor=self.subtensor)

        # Start  starts the miner's axon, making it active on the network.
        self.axon.start()

        bt.logging.info(f"Miner starting at block: {self.block}")

        # This loop maintains the miner's operations until intentionally stopped.
        try:
            while not self.should_exit:
                while (
                    self.block - self.metagraph.last_update[self.uid]
                    < self.config.neuron.epoch_length
                ):
                    # Wait before checking again.
                    time.sleep(1)

                    # Check if we should exit.
                    if self.should_exit:
                        break

                # Sync metagraph and potentially set weights.
                self.sync()
                self.step += 1

        # If someone intentionally stops the miner, it'll safely terminate operations.
        except KeyboardInterrupt:
            self.axon.stop()
            bt.logging.success("Miner killed by keyboard interrupt.")
            exit()

        # In case of unforeseen errors, the miner will log the error and continue operations.
        except Exception:
            bt.logging.error(traceback.format_exc())

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

    def run_in_background_thread(self):
        """
        Starts the miner's operations in a separate background thread.
        This is useful for non-blocking operations.
        """
        if not self.is_running:
            bt.logging.debug("Starting miner in background thread.")
            self.should_exit = False
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.auto_update_thread = threading.Thread(
                target=self.run_auto_update_in_loop, daemon=True
            )
            self.thread.start()
            self.auto_update_thread.start()
            self.is_running = True
            bt.logging.debug("Started")

    def stop_run_thread(self):
        """
        Stops the miner's operations that are running in the background thread.
        """
        if self.is_running:
            bt.logging.debug("Stopping miner in background thread.")
            self.should_exit = True
            self.thread.join(5)
            self.auto_update_thread.join(5)
            self.is_running = False
            bt.logging.debug("Stopped")

    def __enter__(self):
        """
        Starts the miner's operations in a background thread upon entering the context.
        This method facilitates the use of the miner in a 'with' statement.
        """
        self.run_in_background_thread()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Stops the miner's background operations upon exiting the context.
        This method facilitates the use of the miner in a 'with' statement.

        Args:
            exc_type: The type of the exception that caused the context to be exited.
                      None if the context was exited without an exception.
            exc_value: The instance of the exception that caused the context to be exited.
                       None if the context was exited without an exception.
            traceback: A traceback object encoding the stack trace.
                       None if the context was exited without an exception.
        """
        self.save_state()
        self.stop_run_thread()

    def resync_metagraph(self):
        """Resyncs the metagraph and updates the hotkeys and moving averages based on the new metagraph."""
        bt.logging.trace("resync_metagraph()")

        # Sync the metagraph.
        self.metagraph.sync(subtensor=self.subtensor)

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
            state = torch.load(state_path)
            self.neurons_permit_stake = dict(state).get("neurons_permit_stake", {})
        else:
            self.neurons_permit_stake = {}
            bt.logging.warning(
                f"State file not found at {state_path}. Skipping state load."
            )
