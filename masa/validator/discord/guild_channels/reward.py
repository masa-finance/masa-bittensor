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

import torch
import bittensor as bt
from typing import List
from masa.types.discord import DiscordChannelMessageObject


def reward(query: str, response: List[DiscordChannelMessageObject]) -> float:
    # Return a reward of 0.0 if the response is None
    if response is None:
        return 0.0 
    bt.logging.info(f"Getting discord response from {response}")
    guild_id = response.get("guild_id", "")
    bt.logging.info(f"Calculating reward for discord response {guild_id}")
    
    if guild_id == query:
        return 1
    else:
        return 0

def get_rewards(
    self,
    query: str,
    responses: DiscordChannelMessageObject,
) -> torch.FloatTensor:
    bt.logging.info(f"Getting rewards...")
    return torch.FloatTensor(
        [reward(query, response) for response in responses]
    ).to(self.device) 

