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
from neurons.validator import Validator
from masa.base.validator import BaseValidatorNeuron
import bittensor as bt


class TestValidator:

    @pytest.fixture
    async def validator(self):
        config = BaseValidatorNeuron.config()
        config.netuid = 165
        config.subtensor.network = "test"
        config.subtensor.chain_endpoint = "wss://test.finney.opentensor.ai:443"
        config.wallet.name = "subnet_165"
        config.wallet.hotkey = "validator_1"
        config.axon.port = 8092
        config.neuron.dont_save_events = True
        config.neuron.test_mode = True  # Enable test mode to skip registration check
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

        # Add logging for debugging
        bt.logging.info(f"Number of axons in metagraph: {m_axons}")
        bt.logging.info(f"Ping response length: {len(ping_axons_response)}")

        # First assert - check if we have any axons to work with
        assert m_axons > 0, "No axons found in metagraph"
        assert len(ping_axons_response) > 0, "No responses from ping_axons"
        assert m_axons == len(ping_axons_response), "axons length mismatch"

        # Get Twitter profile responses
        response = await validator_instance.forwarder.get_twitter_profile()
        bt.logging.info(f"Twitter profile response length: {len(response)}")

        # Check responses - allow for some miners to fail
        assert (
            len(response) > 0
        ), f"No responses from miners. Metagraph has {m_axons} axons, ping received {len(ping_axons_response)} responses"

        # Validate response structure for successful responses
        for item in response:
            assert "uid" in item, f"'uid' missing from response item: {item}"
            assert "response" in item, f"'response' missing from response item: {item}"

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
