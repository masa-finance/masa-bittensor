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

from neurons.miner import Miner


from masa.base.validator import BaseValidatorNeuron

from bittensor_wallet import Wallet

wallet_validator = Wallet()
wallet_validator.create(coldkey_use_password=False)


class TemplateValidatorNeuronTestCase(unittest.IsolatedAsyncioTestCase):
    """
    This class contains unit tests for the MinerNeuron classes.
    """

    miner = None

    async def asyncSetUp(self):
        config = BaseValidatorNeuron.config()

        config.netuid = 165
        config.subtensor.network = "test"
        config.subtensor.chain_endpoint = "wss://test.finney.opentensor.ai:443"
        config.wallet.name = "validator"
        config.wallet.hotkey = "default"
        config.axon.port = 8092

        self.miner = Miner(config=config)

    def test_validator_has_uid(self):
        uid = self.miner.uid

        self.assertGreater(uid, -1, "UID should be greater than -1 for success")
        return
