# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Masa

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

from masa.utils.uids import get_random_miner_uids
from typing import Any
import bittensor as bt

TIMEOUT = 8


class Forwarder:
    def __init__(self, validator):
        self.validator = validator

    async def send_dendrite_request(
        self, request: Any, sample_size: int = None, timeout: int = TIMEOUT
    ):
        if sample_size is None:
            sample_size = self.validator.config.neuron.sample_size

        miner_uids = await get_random_miner_uids(self.validator, k=sample_size)
        dendrite = bt.dendrite(wallet=self.validator.wallet)
        responses = await dendrite(
            [self.validator.metagraph.axons[uid] for uid in miner_uids],
            request,
            deserialize=True,
            timeout=timeout,
        )
        return responses

    # TODO add all the forwarding logic here!
