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

import bittensor as bt

from masa.protocol import SimpleGETProtocol
from masa.validator.reward import get_rewards
from masa.utils.uids import get_random_uids

class ValidatorNeuron:
    def __init__(self, config):
        self.config = config
        self.dendrite = bt.Dendrite()  # Assuming you have a Dendrite instance for network queries
        self.metagraph = bt.Metagraph()  # Assuming you have a Metagraph instance for network state
        self.scores = {}  # Placeholder for storing miner scores

    async def forward(self):
        """
        The forward function is called by the validator every time step.
        It is responsible for querying the network and scoring the responses.
        """
        try:
            # Define the GET request URL
            request_url = 'http://example.com/api/data'  # Update this URL to your desired endpoint

            # Query miners
            responses = await self.query_miners(request_url)

            # Log the results for monitoring purposes.
            bt.logging.info(f"Received responses: {responses}")

            # Adjust the scores based on responses from miners.
            rewards = get_rewards(self, responses=responses)

            bt.logging.info(f"Scored responses: {rewards}")
            # Update the scores based on the rewards.
            self.update_scores(rewards, [response['uid'] for response in responses])
        except Exception as e:
            bt.logging.error(f"Error during the forward pass: {str(e)}")

    async def query_miners(self, request_url):
        miner_uids = get_random_uids(self, k=self.config.neuron.sample_size)
        responses = await self.dendrite(
            axons=[self.metagraph.axons[uid] for uid in miner_uids],
            synapse=SimpleGETProtocol(request_url=request_url),
            deserialize=True,
        )
        return responses

    def update_scores(self, rewards, miner_uids):
        """
        Update the scores based on the rewards.
        This function assumes a binary scoring system where rewards are either 1.0 (success) or 0.0 (failure).
        """
        for uid, reward in zip(miner_uids, rewards):
            if uid not in self.scores:
                self.scores[uid] = 0.0  # Initialize score if miner UID not found
            
            if reward == 1.0:
                self.scores[uid] += 1.0
            
            bt.logging.info(f"Updated score for miner {uid}: {self.scores[uid]}")

# Example usage
if __name__ == "__main__":
    config = {}  # Define your configuration here
    validator = ValidatorNeuron(config=config)
    # Assuming you have an event loop to run the async forward method
    import asyncio
    asyncio.run(validator.forward())