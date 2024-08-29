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

from masa.utils.uids import get_random_uids
import bittensor as bt

# this forwarder needs to able to handle multiple requests, driven off of an API request


class Forwarder:
    def __init__(self, validator):
        self.validator = validator
        self.minimum_accepted_score = 0.8

    async def forward(
        self,
        request,
        timeout=10,
        limit=None,
    ):
        miner_uids = await get_random_uids(
            self.validator, k=self.validator.config.neuron.sample_size
        )

        bt.logging.info("Calling UIDS -----------------------------------------")
        bt.logging.info(miner_uids)

        if miner_uids is None:
            return []

        synapses = await self.validator.dendrite(
            axons=[self.validator.metagraph.axons[uid] for uid in miner_uids],
            synapse=request,
            deserialize=False,
            timeout=timeout,
        )

        responses = [synapse.response for synapse in synapses]

        # Filter and parse valid responses
        valid_responses, valid_miner_uids = self.sanitize_responses_and_uids(
            responses, miner_uids=miner_uids
        )
        parsed_responses = responses

        process_times = [
            synapse.dendrite.process_time
            for synapse, uid in zip(synapses, miner_uids)
            if uid in valid_miner_uids
        ]

        # Add corresponding uid to each response
        responses_with_metadata = [
            {
                "response": response,
                "uid": int(uid.item()),
                "latency": latency,
            }
            for response, latency, uid in zip(
                parsed_responses, process_times, valid_miner_uids
            )
        ]

        responses_with_metadata.sort(key=lambda x: (x["latency"]))

        for response_metadata in responses_with_metadata:
            miner_uid = response_metadata["uid"]
            volume = len(
                response_metadata["response"]
            )  # Assuming volume is the length of the response
            self.validator.add_volume(miner_uid, volume)

        if limit:
            return responses_with_metadata[: int(limit)]
        return responses_with_metadata

    def sanitize_responses_and_uids(self, responses, miner_uids):
        valid_responses = [response for response in responses if response is not None]
        valid_miner_uids = [
            miner_uids[i]
            for i, response in enumerate(responses)
            if response is not None
        ]
        return valid_responses, valid_miner_uids
