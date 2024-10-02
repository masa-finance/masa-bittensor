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

import unittest
import bittensor as bt

from neurons.validator import Validator

from masa.base.validator import BaseValidatorNeuron
from masa.mock import MockSubtensor

wallet_validator = bt.MockWallet()
wallet_validator.create(coldkey_use_password=False)


class TemplateValidatorNeuronTestCase(unittest.IsolatedAsyncioTestCase):
    """
    This class contains unit tests for the MinerNeuron classes.
    """

    async def asyncSetUp(self):
        subtensor = MockSubtensor(netuid=1, n=4, wallet=wallet_validator)
        neurons = subtensor.neurons(netuid=1)

        config = BaseValidatorNeuron.config()
        config.subtensor._mock = True
        config.mock = True
        # bt.logging.info(f"Config: {config}")

        # TODO: this breaks, complaining about mock_endpoint not being a real URL...
        # note, we may need a real subtensor to test the validator <> miner communication...
        self.validator = Validator(config=config)

    def test_ping_synpase(self):
        return
