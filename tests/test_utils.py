import pytest
import bittensor as bt
from masa.mock import MockMetagraph, MockSubtensor
from masa.utils.uids import get_available_uids, check_uid_availability


user_wallet = bt.MockWallet()
user_wallet.create(coldkey_use_password=False)


@pytest.mark.parametrize("netuid", [42])
@pytest.mark.parametrize("n", [256])
@pytest.mark.parametrize("wallet", [user_wallet])
def test_available_uids(netuid, n, wallet):
    mock_subtensor = MockSubtensor(netuid=netuid, n=n, wallet=wallet)
    mock_metagraph = MockMetagraph(netuid=netuid, subtensor=mock_subtensor)
    available_uids = get_available_uids(mock_metagraph)
    assert len(available_uids) == n


@pytest.mark.parametrize("netuid", [42])
@pytest.mark.parametrize("n", [256])
@pytest.mark.parametrize("uid", [1, 3, 5, 7, 9])
@pytest.mark.parametrize("wallet", [user_wallet])
def test_uid_availability(netuid, n, uid, wallet):
    mock_subtensor = MockSubtensor(netuid=netuid, n=n, wallet=wallet)
    mock_metagraph = MockMetagraph(netuid=netuid, subtensor=mock_subtensor)
    is_available = check_uid_availability(mock_metagraph, uid)
    assert is_available is True
