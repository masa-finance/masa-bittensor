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
from masa.types.web import WebScraperObject


def reward(query: str, response: WebScraperObject) -> float:
    # Return a reward of 0.0 if the response is None
    if response is None:
        return 0.0
    bt.logging.info(f"Getting web scraper response from {response}")

    # Extract length of response
    pages_length = 0
    if isinstance(response["pages"], list):
        pages_length = len(response["pages"])

    bt.logging.info(f"Calculating reward for web scraper response {pages_length}")

    # Return a reward of 1 if the response is not empty and has a length
    if pages_length > 0:
        return 1
    else:
        return 0


def get_rewards(
    self,
    query: str,
    responses: WebScraperObject,
) -> torch.FloatTensor:
    bt.logging.info("Getting rewards...")
    return torch.FloatTensor([reward(query, response) for response in responses]).to(
        self.device
    )
