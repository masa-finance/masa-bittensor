# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

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
import typing
import requests
import bittensor as bt

# Bittensor Miner Template:
import masa

# import base miner class which takes care of most of the boilerplate
from masa.base.miner import BaseMinerNeuron
from masa.api.request import Request
from masa.miner.oracle_request import OracleRequest

delay = 10
class Miner(BaseMinerNeuron):
    def __init__(self, config=None):
        super(Miner, self).__init__(config=config)

    async def forward(
        self, synapse: Request
    ) -> Request:
        bt.logging.info(f"Sleeping for rate limiting purposes: {delay}s")
        time.sleep(delay)
        bt.logging.info(f"Miner needs to fetch profile {synapse.request}")
        try:
            profile = OracleRequest().get_profile(synapse.request)
            bt.logging.info(f"Profile: {profile}")
            if profile != None:
                synapse.twitter_object = profile    

            else:
                bt.logging.error(f"Failed to fetch Twitter profile for {synapse.request}.")
        
        except Exception as e:
            bt.logging.error(f"Exception occurred while fetching Twitter profile for {synapse.request}: {str(e)}")
            
        print("Returning synapse: ", synapse.twitter_object)
        return synapse

    async def blacklist(self, synapse: Request) -> typing.Tuple[bool, str]:
        uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        if not self.config.blacklist.allow_non_registered and synapse.dendrite.hotkey not in self.metagraph.hotkeys:
            bt.logging.trace(f"Blacklisting un-registered hotkey {synapse.dendrite.hotkey}")
            return True, "Unrecognized hotkey"
        if self.config.blacklist.force_validator_permit and not self.metagraph.validator_permit[uid]:
            bt.logging.warning(f"Blacklisting a request from non-validator hotkey {synapse.dendrite.hotkey}")
            return True, "Non-validator hotkey"
        bt.logging.trace(f"Not Blacklisting recognized hotkey {synapse.dendrite.hotkey}")
        return False, "Hotkey recognized!"

    async def priority(self, synapse: Request) -> float:
        caller_uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        priority = float(self.metagraph.S[caller_uid])
        bt.logging.trace(f"Prioritizing {synapse.dendrite.hotkey} with value: ", priority)
        return priority
    
    
    def save_state(state):
        return None

if __name__ == "__main__":
    with Miner() as miner:
        while True:
            bt.logging.info("Miner running...", time.time())
            time.sleep(5)