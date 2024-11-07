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
import asyncio
from neurons.validator import Validator
from masa.base.validator import BaseValidatorNeuron


class TestValidator:

    @pytest.fixture
    async def validator(self):
        config = BaseValidatorNeuron.config()
        config.netuid = 165
        config.subtensor.network = "test"
        config.subtensor.chain_endpoint = "wss://test.finney.opentensor.ai:443"
        config.wallet.name = "validator"
        config.wallet.hotkey = "default"
        config.axon.port = 8092
        config.neuron.dont_save_events = True
        validator_instance = Validator(config=config)
        return validator_instance

    @pytest.mark.asyncio
    async def test_validator_has_uid(self, validator):
        validator_instance = await validator
        uid = validator_instance.uid
        assert uid > -1, "UID should be greater than -1 for success"

    @pytest.mark.asyncio
    async def test_validator_get_twitter_profile(self, validator):
        validator_instance = await validator
        ping_axons_response = await validator_instance.forwarder.ping_axons()
        m_axons = len(validator_instance.metagraph.axons)
        response = await validator_instance.forwarder.get_twitter_profile()

        assert m_axons == len(ping_axons_response), "axons length mismatch"
        assert len(response) > 0, "no response from miners"
        for item in response:
            assert "uid" in item, "property missing"
            assert "response" in item, "property missing"

    @pytest.mark.asyncio
    async def test_validator_get_miners_volumes(self, validator):
        validator_instance = await validator
        await validator_instance.forwarder.ping_axons()
        current_block = validator_instance.last_volume_block
        await validator_instance.forwarder.get_miners_volumes()
        new_block = validator_instance.last_volume_block
        assert current_block != new_block, "miner volume check did not run properly"

    @pytest.mark.asyncio
    async def test_validator_fetch_subnet_config(self, validator):
        validator_instance = await validator
        await validator_instance.forwarder.fetch_subnet_config()
        assert validator_instance.subnet_config != {}, "subnet config is empty"

    @pytest.mark.asyncio
    async def test_validator_fetch_twitter_queries(self, validator):
        validator_instance = await validator
        await validator_instance.forwarder.fetch_twitter_queries()
        assert validator_instance.keywords != [], "keywords are empty"

    # TODO CI/CD not working for this yet...
    # @pytest.mark.asyncio
    # async def test_validator_score_miners(self, validator):
    #     validator_instance = await validator
    #     current_block = validator_instance.last_scoring_block
    #     await validator_instance.forwarder.get_miners_volumes()
    #     await validator_instance.scorer.score_miner_volumes()
    #     new_block = validator_instance.last_scoring_block
    #     assert current_block != new_block, "miner scoring did not run properly"
