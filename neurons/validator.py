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
import json
# Bittensor
import bittensor as bt

# Bittensor Validator Template:
from masa.utils.uids import get_random_uids

# import base validator class which takes care of most of the boilerplate
from masa.base.validator import BaseValidatorNeuron

# masa 
from masa.validator.reward import reward, get_rewards
from masa.api.request import Request
from masa.types import TwitterObject

class Validator(BaseValidatorNeuron):
    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)
        bt.logging.info("load_state()")
        self.load_state()

    async def forward(self):
        try:
            profile = 'brendanplayford'
            print(f"Requesting profile: {profile}")
            
            # Getting responses, parsing them from JSON to dict, then to TwitterObject
            [miner_uids, responses] = await self.query_miners(profile)
            
            print(f"Responses: {responses}")
            if responses is not None and any(response is not None for response in responses):
                
                    
                
                if isinstance(responses, list) and responses:
                    bt.logging.info("Responses is a list")
                    valid_responses = []
                    valid_miner_uids = []
                    for i, response in enumerate(responses):
                        if response is not None:
                            valid_responses.append(response)
                            valid_miner_uids.append(miner_uids[i])
                    responses = valid_responses
                    miner_uids = valid_miner_uids
                    parsed_responses = [TwitterObject(**response) for response in valid_responses]
                    
                    bt.logging.info(f"Parsed responses: {parsed_responses}")
                
                    
                    rewards = get_rewards(self, query=profile, responses=parsed_responses)
                    bt.logging.info(f"Miner UIDS: {valid_miner_uids}")
                    bt.logging.info(f"Rewards: {rewards}")
                    
                    
                    
                    if len(rewards) > 0:
                        print(f"Updating scores {rewards} {valid_miner_uids}")
                        self.update_scores(rewards, valid_miner_uids)

        except Exception as e:
            bt.logging.error(f"Error during the forward pass: {str(e)}")

    async def query_miners(self, prompt):
        print("QUERY MINERS")
        print(f"Sample size :{self.config.neuron.sample_size}")
        # Example: Querying miners using the dendrite object
        miner_uids = get_random_uids(self, k=self.config.neuron.sample_size)
        print("QUERY MINERS", miner_uids)
        responses = await self.dendrite(
            axons=[self.metagraph.axons[uid] for uid in miner_uids],
            synapse=Request(request=prompt),
            deserialize=True,
        )
        return [miner_uids, responses]

    def score_response(self, response, reference):
         # Use the reward function from reward.py to maintain consistency
        return reward(reference, response)

    def update_weights(self, scores):
        # Example: Update weights (this is a placeholder for actual weight update logic)
        for score in scores:
            # TODO Update logic here
            pass

if __name__ == "__main__":
    with Validator() as validator:
        while True:
            bt.logging.info("Validator running...", time.time())
            time.sleep(5)