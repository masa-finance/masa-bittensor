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
import bittensor as bt


# this forwarder needs to able to handle multiple requests, driven off of an API request
class Forwarder:
    def __init__(self, validator):
        self.validator = validator

    async def forward(
        self, request, get_rewards, parser_object=None, parser_method=None, timeout=5
    ):
        # TODO: This should live inside each endpoint to enable us to filter miners by different parameters in the future
        # like blacklisting miners only on a specific endpoint like profiles or followers
        miner_uids = await get_random_uids(
            self.validator, k=self.validator.config.neuron.sample_size
        )

        if miner_uids is None:
            return []

        responses = await self.validator.dendrite(
            axons=[self.validator.metagraph.axons[uid] for uid in miner_uids],
            synapse=request,
            deserialize=True,
            timeout=timeout,
        )

        # Filter and parse valid responses
        valid_responses, valid_miner_uids = self.sanitize_responses_and_uids(
            responses, miner_uids=miner_uids
        )
        parsed_responses = responses

        if parser_object:
            parsed_responses = [
                parser_object(**response) for response in valid_responses
            ]
        elif parser_method:
            parsed_responses = parser_method(valid_responses)

        # Score responses
        rewards = get_rewards(
            self.validator, query=request.query, responses=parsed_responses
        )

        # Update the scores based on the rewards

        if len(valid_miner_uids) > 0:
            self.validator.update_scores(rewards, valid_miner_uids)
            if self.validator.should_set_weights():
                try:
                    self.validator.set_weights()
                except Exception as e:
                    bt.logging.error(f"Failed to set weights: {e}")
                    
        # Add corresponding uid to each response
        response_with_uids = [
            {"response": response, "uid": int(uid.item()), "score": score.item()}
            for response, uid, score in zip(parsed_responses, valid_miner_uids, rewards)
        ]
            
        response_with_uids.sort(key=lambda x: x["score"], reverse=True)
        
        print("FINAL RESPONSES ------------------------------------------------")
        print(response_with_uids)
        
        return response_with_uids

    def sanitize_responses_and_uids(self, responses, miner_uids):
        valid_responses = [response for response in responses if response is not None]
        valid_miner_uids = [
            miner_uids[i]
            for i, response in enumerate(responses)
            if response is not None
        ]
        return valid_responses, valid_miner_uids
