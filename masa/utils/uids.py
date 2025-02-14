import torch
import random
import bittensor as bt
from typing import List


def check_uid_availability(metagraph: "bt.metagraph.Metagraph", uid: int) -> bool:
    """
    Check if uid is available. The UID should be available if it is serving and has less
    than vpermit_tao_limit stake

    Args:
        metagraph (:obj: bt.metagraph.Metagraph): Metagraph object
        uid (int): uid to be checked
        vpermit_tao_limit (int): Validator permit tao limit
    Returns:
        bool: True if uid is available, False otherwise
    """
    # Filter non serving axons.
    if not metagraph.axons[uid].is_serving:
        bt.logging.info(f"UID: {uid} is not serving")
        return False

    # Filter out non validator permit.
    if metagraph.validator_permit[uid]:

        # Filter out uid without IP.
        if metagraph.neurons[uid].axon_info.ip == "0.0.0.0":
            return False

    # Available otherwise.
    return True


def get_available_uids(metagraph: "bt.metagraph.Metagraph") -> List[int]:
    return [
        uid
        for uid in range(metagraph.n.item())
        if check_uid_availability(metagraph, uid)
    ]


def remove_excluded_uids(uids: List[int], exclude: List[int] = None) -> List[int]:
    if exclude is None:
        return uids
    return [uid for uid in uids if uid not in exclude]


async def get_random_miner_uids(
    self, k: int, exclude: List[int] = None
) -> torch.LongTensor:
    """
    Returns at most k available random uids from the metagraph.

    Args:
        k (int): Number of uids to return.
        exclude (List[int]): List of uids to exclude from the random sampling.
    Returns:
        uids (torch.LongTensor): Randomly sampled available uids.
    Notes:
        If `k` is larger than the number of available `uids`, set `k` to the number of
        available `uids`.
    """
    try:
        # Generic sanitation
        avail_uids = get_available_uids(self.metagraph)
        healthy_uids = remove_excluded_uids(avail_uids, exclude)
        subnet_params = await self.subtensor.get_subnet_hyperparameters(
            self.config.netuid
        )
        weights_version = subnet_params.weights_version

        version_checked_uids = [
            uid for uid in healthy_uids if self.versions[uid] >= weights_version
        ]

        k = min(k, len(version_checked_uids))
        random_sample = random.sample(version_checked_uids, k)
        uids = torch.tensor(random_sample)
        return uids
    except Exception as e:
        bt.logging.error(f"Failed to get random miner uids: {e}")
        return None


async def get_uncalled_miner_uids(
    self, k: int, exclude: List[int] = None
) -> torch.LongTensor:
    """
    Returns at most k available random uids from the metagraph.

    Args:
        k (int): Number of uids to return.
        exclude (List[int]): List of uids to exclude from the random sampling.
    Returns:
        uids (torch.LongTensor): Randomly sampled available uids.
    Notes:
        If `k` is larger than the number of available `uids`, set `k` to the number of
        available `uids`.
    """
    try:
        if len(self.uncalled_uids) == 0:
            # Generic sanitation
            avail_uids = get_available_uids(self.metagraph)
            healthy_uids = remove_excluded_uids(avail_uids, exclude)
            subnet_params = await self.subtensor.get_subnet_hyperparameters(
                self.config.netuid
            )
            weights_version = subnet_params.weights_version
            version_checked_uids = [
                uid for uid in healthy_uids if self.versions[uid] >= weights_version
            ]
            self.uncalled_uids = set(version_checked_uids)

        k = min(k, len(self.uncalled_uids))
        random_sample = random.sample(list(self.uncalled_uids), k)
        bt.logging.info(f"Calling uids: {random_sample}")
        self.uncalled_uids.difference_update(random_sample)
        bt.logging.info(f"Remaining uids: {list(self.uncalled_uids)}")
        uids = torch.tensor(random_sample)
        return uids
    except Exception as e:
        bt.logging.error(f"Failed to get uncalled miner uids: {e}")
        return None
