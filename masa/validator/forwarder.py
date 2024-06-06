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

from masa.utils.uids import get_random_uids

# this forwarder needs to able to handle multiple requests, driven off of an API request
class Forwarder:
    def __init__(self, validator):
        self.validator = validator
        self.miner_uids = get_random_uids(validator, k=validator.config.neuron.sample_size)
        
        
    async def forward(self, request, get_rewards, query, parser = None):
        responses = await self.validator.dendrite(
            axons=[self.validator.metagraph.axons[uid] for uid in self.miner_uids],
            synapse=request,
            deserialize=True,
        )

        # Filter and parse valid responses
        valid_responses, valid_miner_uids = self.sanitize_responses_and_uids(responses)
        parsed_responses = responses
        
        if parser:
            parsed_responses = [parser(**response) for response in valid_responses]

        # Score responses
        rewards = get_rewards(self.validator, query=query, responses=parsed_responses)

        # Update the scores based on the rewards
        self.validator.update_scores(rewards, valid_miner_uids)
        

    def sanitize_responses_and_uids(self, responses):
        valid_responses = [response for response in responses if response is not None]
        valid_miner_uids = [self.miner_uids[i] for i, response in enumerate(responses) if response is not None]
        return valid_responses, valid_miner_uids