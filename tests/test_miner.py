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
from neurons.miner import Miner
from masa.base.miner import BaseMinerNeuron
from tests.test_subnet import analyze_subnet


def get_best_miner_hotkey(netuid: int = 165, network: str = "test") -> str:
    """Get the best miner hotkey based on emissions."""
    subnet_data = analyze_subnet(netuid=netuid, network=network)
    miners = subnet_data["miners"]

    # Sort by emissions (higher is better)
    miners.sort(key=lambda x: x["emissions"], reverse=True)

    if not miners:
        pytest.skip("No miners found in subnet")

    best_miner = miners[0]
    bt.logging.info(f"Selected miner UID {best_miner['uid']}")
    bt.logging.info(f"Emissions: {best_miner['emissions']:.4f}")
    bt.logging.info(f"Stake: τ{best_miner['stake']:.2f}")

    return best_miner["hotkey"]


class TestMiner:
    @pytest.fixture
    async def miner(self):
        config = BaseMinerNeuron.config()
        config.netuid = 165
        config.subtensor.network = "test"
        config.subtensor.chain_endpoint = "wss://test.finney.opentensor.ai:443"

        # Get best miner hotkey
        miner_hotkey = get_best_miner_hotkey()
        bt.logging.info(f"Using miner hotkey: {miner_hotkey}")

        config.wallet.name = "default"
        config.wallet.hotkey = miner_hotkey

        config.axon.port = 8091
        config.neuron.dont_save_events = True
        miner_instance = Miner(config=config)
        return miner_instance

    @pytest.mark.asyncio
    async def test_miner_has_uid(self, miner):
        """Test that the miner has a valid UID."""
        miner_instance = await miner
        uid = miner_instance.uid
        assert uid > -1, "UID should be greater than -1 for success"

    @pytest.mark.asyncio
    async def test_miner_blacklist(self, miner):
        """Test the miner's blacklist functionality."""
        miner_instance = await miner

        # Create a mock synapse with the miner's own hotkey
        class MockSynapse:
            class MockDendrite:
                def __init__(self, hotkey):
                    self.hotkey = hotkey

            def __init__(self, hotkey):
                self.dendrite = self.MockDendrite(hotkey)

        # Test with miner's own hotkey (should not be blacklisted)
        mock_synapse = MockSynapse(miner_instance.wallet.hotkey.ss58_address)
        is_blacklisted, reason = await miner_instance.blacklist(mock_synapse)
        assert (
            not is_blacklisted
        ), f"Miner should not blacklist itself, but got reason: {reason}"

    @pytest.mark.asyncio
    async def test_miner_config(self, miner):
        """Test the miner's configuration."""
        miner_instance = await miner
        assert miner_instance.config.netuid == 165, "Incorrect netuid"
        assert miner_instance.config.subtensor.network == "test", "Incorrect network"
        assert miner_instance.config.wallet.name == "default", "Incorrect wallet name"
        assert miner_instance.config.wallet.hotkey is not None, "No hotkey configured"
