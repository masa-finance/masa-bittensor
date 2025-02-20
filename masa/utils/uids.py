import torch
import random
import bittensor as bt
from typing import List


def check_uid_availability(metagraph: "bt.metagraph.Metagraph", uid: int) -> bool:
    """
    Check if uid is available. The UID should be available if:
    1. It is not a validator (validator_trust == 0)
    2. It is serving
    3. Has proper validator permit configuration

    Args:
        metagraph (:obj: bt.metagraph.Metagraph): Metagraph object
        uid (int): uid to be checked
    Returns:
        bool: True if uid is available, False otherwise
    """
    # First filter out validators
    if metagraph.validator_trust[uid] > 0:
        return False

    # Then filter non serving axons
    if not metagraph.axons[uid].is_serving:
        hotkey = metagraph.hotkeys[uid]
        bt.logging.info(
            f"Miner {uid} is not serving - https://taostats.io/hotkey/{hotkey}"
        )
        return False

    # Available if it's a serving miner
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

            # Ensure versions list is properly sized
            if len(self.versions) < self.metagraph.n.item():
                self.versions = [0] * self.metagraph.n.item()

            version_checked_uids = [
                uid
                for uid in healthy_uids
                if uid < len(self.versions) and self.versions[uid] >= weights_version
            ]
            self.uncalled_uids = set(version_checked_uids)

        k = min(k, len(self.uncalled_uids))
        if k == 0:
            bt.logging.warning("No available uncalled UIDs found")
            return None

        random_sample = random.sample(list(self.uncalled_uids), k)
        bt.logging.info(
            f"📋 Selected {len(random_sample)} miners | UIDs: {random_sample}"
        )
        self.uncalled_uids.difference_update(random_sample)
        bt.logging.debug(f"Remaining UIDs in pool: {list(self.uncalled_uids)}")
        uids = torch.tensor(random_sample)
        return uids
    except Exception as e:
        bt.logging.error(f"Failed to get uncalled miner uids: {e}")
        return None
