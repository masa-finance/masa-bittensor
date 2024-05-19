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
from masa.utils.uids import get_random_uids

async def forward(self):
    """
    The forward function is called by the validator every time step.
    """
    request_url = 'http://localhost:8080/api/v1/data/twitter/profile/brendanplayford'
    miner_uids = get_random_uids(self, k=self.config.neuron.sample_size)

    responses = await self.dendrite(
        axons=[self.metagraph.axons[uid] for uid in miner_uids],
        synapse=SimpleGETProtocol(request_url=request_url),
        deserialize=True,
    )

    bt.logging.info(f"Received responses: {responses}")

    # Process responses and update scores
    for uid, response in zip(miner_uids, responses):
        if response_is_valid(response):
            update_miner_score(uid, increase=True)
            bt.logging.info(f"Updated score for miner {uid}: Increased")
        else:
            update_miner_score(uid, increase=False)
            bt.logging.info(f"Updated score for miner {uid}: Decreased")

def response_is_valid(response):
    """
    Checks if the response from a miner contains expected data.
    
    Args:
    - response (dict): The response received from a miner.
    
    Returns:
    - bool: True if the response is valid, False otherwise.
    """
    # Example: Check if the response contains an 'expected_key' - this would be something like the PK of a profile such as the userID
    expected_key = "data"
    return expected_key in response and isinstance(response[expected_key], dict)  # Further checks can be added

def update_miner_score(uid, increase=True):
    """
    Updates the score of a miner based on the validity of their response.
    
    Args:
    - uid (int): The unique identifier of the miner.
    - increase (bool): Whether to increase or decrease the miner's score.
    """
    # Placeholder for score update logic
    # This could involve interacting with the metagraph or another component managing scores
    
    # Example pseudo-code:
    score_change = 1 if increase else -1
    current_score = get_current_score(uid)  # Assume this function retrieves the current score
    new_score = max(0, current_score + score_change)  # Ensure scores do not go negative
    set_new_score(uid, new_score)  # Assume this function updates the score
    
    # Log the score update for monitoring
    action = "Increased" if increase else "Decreased"
    bt.logging.info(f"Score for miner {uid} {action} to {new_score}.")