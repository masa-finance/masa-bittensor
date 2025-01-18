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
import asyncio  # Required for pytest.mark.asyncio
import bittensor as bt
from neurons.validator import Validator
from masa.base.validator import BaseValidatorNeuron
from tests.test_subnet import analyze_subnet


def get_best_validator_hotkey(netuid: int = 165, network: str = "test") -> str:
    """Get the best validator hotkey based on trust and active status."""
    subnet_data = analyze_subnet(netuid=netuid, network=network)
    validators = subnet_data["validators"]

    # Sort by trust and active status
    validators.sort(key=lambda x: (x["trust"], x["active"]), reverse=True)

    if not validators:
        pytest.skip("No validators found in subnet")

    best_validator = validators[0]
    bt.logging.info(f"Selected validator UID {best_validator['uid']}")
    bt.logging.info(f"Trust: {best_validator['trust']:.4f}")
    bt.logging.info(f"Active: {best_validator['active']}")
    bt.logging.info(f"Stake: τ{best_validator['stake']:.2f}")

    return best_validator["hotkey"]


class TestValidator:
    @pytest.fixture
    async def validator(self):
        config = BaseValidatorNeuron.config()
        config.netuid = 165
        config.subtensor.network = "test"
        config.subtensor.chain_endpoint = "wss://test.finney.opentensor.ai:443"

        # Get best validator hotkey
        validator_hotkey = get_best_validator_hotkey()
        bt.logging.info(f"Using validator hotkey: {validator_hotkey}")

        config.wallet.name = "default"
        config.wallet.hotkey = validator_hotkey

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

        # Track miners with real IPs
        real_ip_miners = []
        for axon in validator_instance.metagraph.axons:
            if axon.ip and axon.ip != "0.0.0.0":
                bt.logging.info(f"Found miner with real IP: {axon.ip}:{axon.port}")
                real_ip_miners.append({"ip": axon.ip, "port": axon.port})

        bt.logging.info(
            f"Found {len(real_ip_miners)} miners with real IPs out of {m_axons} total miners"
        )

        # Get responses
        response = await validator_instance.forwarder.get_twitter_profile()

        # Track responses by IP
        responses_by_ip = {}
        for item in response:
            if "uid" in item and item["uid"] < len(validator_instance.metagraph.axons):
                axon = validator_instance.metagraph.axons[item["uid"]]
                if axon.ip != "0.0.0.0":
                    responses_by_ip[f"{axon.ip}:{axon.port}"] = item.get("response")

        if responses_by_ip:
            bt.logging.info(f"Received responses from: {list(responses_by_ip.keys())}")
        else:
            bt.logging.warning("No responses received from any miners with real IPs")

        # Basic test assertions
        assert m_axons == len(ping_axons_response), "axons length mismatch"
        assert isinstance(response, list), "response should be a list"
        for item in response:
            assert "uid" in item, "property missing"
            assert "response" in item, "property missing"

        # Report on real IP miners
        assert len(real_ip_miners) > 0, "No miners found with real IPs"

    @pytest.mark.asyncio
    async def test_validator_get_miners_volumes(self, validator):
        validator_instance = await validator
        await validator_instance.forwarder.ping_axons()

        current_block = validator_instance.block
        current_volume_block = validator_instance.last_volume_block

        await validator_instance.forwarder.get_miners_volumes()

        assert (
            validator_instance.last_volume_block >= current_volume_block
        ), "volume check should update or maintain last_volume_block"
        assert (
            validator_instance.block >= current_block
        ), "block number should advance or stay the same"

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
