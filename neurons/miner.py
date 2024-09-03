# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Masa

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

import time
from typing import Any, Tuple
import bittensor as bt

from masa.base.miner import BaseMinerNeuron

from masa.miner.twitter.profile import TwitterProfileSynapse
from masa.miner.twitter.followers import TwitterFollowersSynapse
from masa.miner.twitter.tweets import RecentTweetsSynapse


class Miner(BaseMinerNeuron):
    def __init__(self, config=None):
        super(Miner, self).__init__(config=config)
        bt.logging.info("Miner initialized with config: {}".format(config))

    async def blacklist_twitter_profile(
        self, synapse: TwitterProfileSynapse
    ) -> Tuple[bool, str]:
        return await self.blacklist(synapse)

    async def blacklist_twitter_followers(
        self, synapse: TwitterFollowersSynapse
    ) -> Tuple[bool, str]:
        return await self.blacklist(synapse)

    async def blacklist_recent_tweets(
        self, synapse: RecentTweetsSynapse
    ) -> Tuple[bool, str]:
        return await self.blacklist(synapse)

    async def blacklist(self, synapse: Any) -> Tuple[bool, str]:
        if self.check_tempo(synapse):
            self.check_stake(synapse)

        hotkey = synapse.dendrite.hotkey
        uid = self.metagraph.hotkeys.index(hotkey)

        bt.logging.trace(f"Neurons Staked: {self.neurons_permit_stake}")
        bt.logging.trace(f"Validator Permit: {self.metagraph.validator_permit[uid]}")

        if (
            not self.config.blacklist.allow_non_registered
            and hotkey not in self.metagraph.hotkeys
        ):
            bt.logging.warning(f"Blacklisting un-registered hotkey {hotkey}")
            return True, "Unrecognized hotkey"
        if (
            self.config.blacklist.force_validator_permit
            and not self.metagraph.validator_permit[uid]
        ):
            bt.logging.warning(
                f"Blacklisting a request from non-validator hotkey {hotkey}"
            )
            return True, "Non-validator hotkey"
        if hotkey not in self.neurons_permit_stake.keys():
            bt.logging.warning(
                f"Blacklisting a request from neuron without enough staked: {hotkey}"
            )
            return True, "Non-staked neuron"

        bt.logging.trace(f"Not Blacklisting recognized hotkey {hotkey}")
        return False, "Hotkey recognized!"

    async def priority_twitter_profile(self, synapse: TwitterProfileSynapse) -> float:
        return await self.priority(synapse)

    async def priority_twitter_followers(
        self, synapse: TwitterFollowersSynapse
    ) -> float:
        return await self.priority(synapse)

    async def priority_recent_tweets(self, synapse: RecentTweetsSynapse) -> float:
        return await self.priority(synapse)

    async def priority(self, synapse: Any) -> float:
        caller_uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        priority = float(self.metagraph.S[caller_uid])
        bt.logging.trace(
            f"Prioritizing {synapse.dendrite.hotkey} with value: ", priority
        )
        return priority

    def check_stake(self, synapse: Any):
        current_stakes = self.metagraph.S
        hotkey = synapse.dendrite.hotkey
        uid = self.metagraph.hotkeys.index(hotkey)
        current_block = self.subtensor.get_current_block()

        if current_stakes[uid] < self.min_stake_required:
            if hotkey in self.neurons_permit_stake.keys():
                del self.neurons_permit_stake[hotkey]
                bt.logging.info(
                    f"Removed neuron {hotkey} from staked list due to insufficient stake."
                )
        else:
            self.neurons_permit_stake[hotkey] = current_block
            bt.logging.info(f"Added neuron {hotkey} to staked list.")

    def check_tempo(self, synapse: Any) -> bool:
        hotkey = synapse.dendrite.hotkey
        last_checked_block = self.neurons_permit_stake.get(hotkey)
        if last_checked_block is None:
            bt.logging.info("There is no last checked block, starting tempo check...")
            return True

        blocks_since_last_check = (
            self.subtensor.get_current_block() - last_checked_block
        )
        if (
            blocks_since_last_check
            >= self.subtensor.get_subnet_hyperparameters(self.config.netuid).tempo
        ):
            bt.logging.trace(
                f"A tempo has passed.  Blocks since last check: {blocks_since_last_check}"
            )
            return True
        else:
            bt.logging.trace(
                f"Not yet a tempo since last check. Blocks since last check: {blocks_since_last_check}"
            )
            return False


if __name__ == "__main__":
    with Miner() as miner:
        while True:
            time.sleep(5)
