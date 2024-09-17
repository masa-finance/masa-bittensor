import pytest
import asyncio
import bittensor as bt
from masa.mock import MockDendrite, MockMetagraph, MockSubtensor
from masa.base.healthcheck import PingAxonSynapse


@pytest.mark.parametrize("netuid", [42])
@pytest.mark.parametrize("n", [256])
@pytest.mark.parametrize("wallet", [bt.MockWallet(), None])
def test_mock_subtensor(netuid, n, wallet):
    subtensor = MockSubtensor(netuid=netuid, n=n, wallet=wallet)
    neurons = subtensor.neurons(netuid=netuid)

    # assertions
    assert subtensor.subnet_exists(netuid)
    assert subtensor.network == "mock"
    assert subtensor.chain_endpoint == "mock_endpoint"
    assert len(neurons) == n
    # check wallet
    if wallet is not None:
        assert subtensor.is_hotkey_registered(
            netuid=netuid, hotkey_ss58=wallet.hotkey.ss58_address
        )
    # check neurons
    for neuron in neurons:
        assert isinstance(neuron, bt.NeuronInfo)
        assert subtensor.is_hotkey_registered(netuid=netuid, hotkey_ss58=neuron.hotkey)


@pytest.mark.parametrize("netuid", [42])
@pytest.mark.parametrize("n", [256])
def test_mock_metagraph(netuid, n):
    wallet = bt.MockWallet()
    mock_subtensor = MockSubtensor(netuid=netuid, n=n, wallet=wallet)
    mock_metagraph = MockMetagraph(netuid=netuid, subtensor=mock_subtensor)

    # check axons
    axons = mock_metagraph.axons
    assert len(axons) == n
    # check ip and port
    for axon in axons:
        assert isinstance(axon, bt.AxonInfo)


@pytest.mark.parametrize("netuid", [42])
@pytest.mark.parametrize("n", [256])
def test_mock_dendrite_timings(netuid, n):
    mock_wallet = bt.MockWallet()
    mock_dendrite = MockDendrite(mock_wallet)
    mock_dendrite.min_time = 0
    mock_dendrite.max_time = 5
    mock_subtensor = MockSubtensor(netuid=netuid, n=n)
    mock_metagraph = MockMetagraph(netuid=netuid, subtensor=mock_subtensor)
    axons = mock_metagraph.axons

    async def run():
        return await mock_dendrite(
            axons,
            synapse=PingAxonSynapse(sent_from="test", is_active=True, version=0),
            timeout=3,
            deserialize=False,
        )

    # TODO can we test here that miners pass back the right version at a first step?
    responses = asyncio.run(run())
    for synapse in responses:
        # bt.logging.info(f"Synapse: {synapse}")
        assert synapse.is_active
