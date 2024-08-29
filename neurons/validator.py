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
import time

# Bittensor Validator Template:
from masa.base.validator import BaseValidatorNeuron
from masa.api.validator_api import ValidatorAPI
from sentence_transformers import SentenceTransformer
from masa.validator.scorer import Scorer


class Validator(BaseValidatorNeuron):
    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)
        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )  # Load a pre-trained model for embeddings
        self.scorer = Scorer(self)
        self.API = ValidatorAPI(self)
        bt.logging.info("Validator initialized with config: {}".format(config))

    def add_volume(self, miner_uid, volume):
        """
        Adds the volume returned by a miner to the block counter, grouped every 360 blocks.

        Args:
            miner_uid (str): The unique identifier of the miner.
            volume (float): The volume to be added.
        """
        current_block = bt.metagraph(42).block  # Get the current block number
        block_group = current_block // 360  # Group blocks by 360

        if not self.volumes or self.volumes[-1]["block_group"] != block_group:
            # If volumes list is empty or the last entry is not for the current block group, add a new entry
            self.volumes.append({"block_group": block_group, "miners": {}})

        if miner_uid not in self.volumes[-1]["miners"]:
            self.volumes[-1]["miners"][miner_uid] = 0

        self.volumes[-1]["miners"][miner_uid] += volume

    async def forward(self):
        pass


if __name__ == "__main__":
    with Validator() as validator:
        while True:
            time.sleep(5)
