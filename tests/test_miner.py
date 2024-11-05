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

import pytest
from neurons.miner import Miner
from masa.base.miner import BaseMinerNeuron


class TestMiner:

    @pytest.fixture
    async def miner(self):
        config = BaseMinerNeuron.config()
        config.netuid = 165
        config.subtensor.network = "test"
        config.subtensor.chain_endpoint = "wss://test.finney.opentensor.ai:443"
        config.wallet.name = "miner"
        config.wallet.hotkey = "default"
        config.blacklist.force_validator_permit = True
        config.axon.port = 8091

        miner_instance = Miner(config=config)
        return miner_instance

    @pytest.mark.asyncio
    async def test_miner_has_uid(self, miner):
        miner_instance = await miner
        uid = miner_instance.uid
        assert uid > -1, "UID should be greater than -1 for success"
