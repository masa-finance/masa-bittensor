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
from masa.validator import forward
from masa.utils.uids import get_random_uids

# import base validator class which takes care of most of the boilerplate
from masa.base.validator import BaseValidatorNeuron

# masa 
from masa.protocol import SimpleGETProtocol 


class Validator(BaseValidatorNeuron):
    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)
        bt.logging.info("Validator initialized and state loaded.")

    async def forward(self):
        """
        Validator forward pass. Consists of:
        - Forwarding the GET request to miners
        - Getting the responses
        """
        try:
            # Define the GET request URL (could be loaded from .env file)
            request_url = 'http://localhost:8080/api/v1/data/twitter/profile/brendanplayford'

            # Query miners
            responses = await self.query_miners(request_url)

            # Here you would process the responses as needed
            # For example, logging them or aggregating results
            bt.logging.info(f"Received responses: {responses}")
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

if __name__ == "__main__":
    with Validator() as validator:
        while True:
            bt.logging.info("Validator running...")
            time.sleep(5)