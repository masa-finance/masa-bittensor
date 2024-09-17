# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Opentensor Foundation

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

import sys
import torch
import unittest
import bittensor as bt

from neurons.miner import Miner

from masa.utils.uids import get_random_miner_uids
from masa.base.miner import BaseMinerNeuron
from masa.base.validator import BaseValidatorNeuron
from masa.mock import MockSubtensor, MockMetagraph, MockDendrite


class TemplateValidatorNeuronTestCase(unittest.IsolatedAsyncioTestCase):
    """
    This class contains unit tests for the MinerNeuron classes.
    """

    async def asyncSetUp(self):
        # sys.argv = sys.argv[0] + ["--config", "tests/configs/miner.json"]

        config = BaseValidatorNeuron.config()
        config.mock = True

        # config.wallet._mock = True
        # config.metagraph._mock = True
        # config.subtensor._mock = True

        self.neuron = BaseValidatorNeuron(config)
        self.miner_uids = await get_random_miner_uids(self.neuron, k=10)
        # bt.logging.info(f"Miner UIDs: {self.miner_uids}")

        # self.miner1 = Miner(config)
        # self.miner2 = Miner(config)
        # self.miner3 = Miner(config)
        # self.subtensor = MockSubtensor(netuid=1, n=4, wallet=wallet)

    async def test_ping_synpase(self):
        assert True
