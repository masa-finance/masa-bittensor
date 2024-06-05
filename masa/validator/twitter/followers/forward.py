# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

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

import bittensor as bt
from masa.api.request import Request, RequestType
from masa.validator.forwarder import Forwarder
from masa.validator.twitter.followers.reward import get_rewards
from masa.types.twitter import TwitterFollowerObject

class FollowersForwarder(Forwarder):

    def __init__(self, validator):
        super(FollowersForwarder, self).__init__(validator)


    async def query_and_score(self, query):
        try:
            # Query miners
            responses = await self.validator.dendrite(
                axons=[self.validator.metagraph.axons[uid] for uid in self.miner_uids],
                synapse=Request(query=query, type=RequestType.TWITTER_FOLLOWERS.value),
                deserialize=True,
            )

            # Filter and parse valid responses
            valid_responses, valid_miner_uids = self.sanitize_responses_and_uids(responses)
            parsed_responses = [
                [TwitterFollowerObject(**follower) for follower in response]
                for response in valid_responses  # Each response is a list of dictionaries
            ]

            # Score responses
            rewards = get_rewards(self.validator, query=query, responses=parsed_responses)

            # Update the scores based on the rewards
            self.validator.update_scores(rewards, valid_miner_uids)

            # Return the valid responses
            return valid_responses

        except Exception as e:
            bt.logging.error(f"Error during the handle responses process: {str(e)}")
            return []