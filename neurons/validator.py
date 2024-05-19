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

# Bittensor
import bittensor as bt

# Bittensor Validator Template:
import alchemy
from alchemy.validator import forward
from alchemy.utils.uids import get_random_uids

# import base validator class which takes care of most of the boilerplate
from alchemy.base.validator import BaseValidatorNeuron

# alchemy 
from alchemy.protocol import JSONProtocol 
from alchemy.validator.reward import reward


class Validator(BaseValidatorNeuron):
    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)
        bt.logging.info("load_state()")
        self.load_state()

    async def forward(self):
        """
        Validator forward pass. Consists of:
        - Generating the query
        - Querying the miners
        - Getting the responses
        - Rewarding the miners
        - Updating the scores
        """
        try:
            # Generate challenge
            unstructured_json = '{"name": "John", "age": "30 years", "city": "New York"}'
            prompt = f"Convert the following unstructured JSON to structured JSON: {unstructured_json}"
            reference = {"name": "John", "age": 30, "city": "New York"}

            # Query miners
            responses = await self.query_miners(prompt)

            # Score responses
            scores = [self.score_response(response, reference) for response in responses]

            # Update weights
            self.update_weights(scores)
        except Exception as e:
            bt.logging.error(f"Error during the forward pass: {str(e)}")

    async def query_miners(self, prompt):
        # Example: Querying miners using the dendrite object
        miner_uids = get_random_uids(self, k=self.config.neuron.sample_size)
        responses = await self.dendrite(
            axons=[self.metagraph.axons[uid] for uid in miner_uids],
            synapse=JSONProtocol(unstructured_json=prompt),
            deserialize=True,
        )
        return responses

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