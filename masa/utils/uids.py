from typing import List
import random
import bittensor as bt


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


async def get_random_miner_uids(validator, k: int = 10) -> List[int]:
    """Get k random miner UIDs that haven't been called yet."""
    # Get all UIDs that are not serving
    not_serving = []
    for uid in range(len(validator.metagraph.uids)):
        if (
            validator.metagraph.axons[uid].ip == "0.0.0.0"
            or validator.metagraph.axons[uid].port == 0
        ):
            not_serving.append(uid)
            bt.logging.debug(f"UID: {uid} is not serving")

    # Get all available UIDs (excluding those not serving)
    available_uids = [
        uid for uid in range(len(validator.metagraph.uids)) if uid not in not_serving
    ]

    # Get random sample of size k
    if len(available_uids) < k:
        k = len(available_uids)
    selected_uids = random.sample(available_uids, k)

    # Calculate remaining UIDs
    remaining_uids = [uid for uid in available_uids if uid not in selected_uids]

    bt.logging.info(
        f"Selected {len(selected_uids)} unique UIDs for calling, {len(remaining_uids)} UIDs remaining"
    )

    return selected_uids


async def get_uncalled_miner_uids(validator, k: int = 10) -> List[int]:
    """Get k miner UIDs that haven't been called yet."""
    # Get all UIDs that are not serving
    not_serving = []
    for uid in range(len(validator.metagraph.uids)):
        if (
            validator.metagraph.axons[uid].ip == "0.0.0.0"
            or validator.metagraph.axons[uid].port == 0
        ):
            not_serving.append(uid)
            bt.logging.debug(f"UID: {uid} is not serving")

    # Get all available UIDs (excluding those not serving and those already called)
    available_uids = [
        uid
        for uid in range(len(validator.metagraph.uids))
        if uid not in not_serving and uid not in validator.uncalled_uids
    ]

    # Get first k UIDs
    if len(available_uids) < k:
        k = len(available_uids)
    selected_uids = available_uids[:k]

    # Update uncalled_uids set
    validator.uncalled_uids.update(selected_uids)

    # Calculate remaining uncalled UIDs
    remaining_uncalled = [uid for uid in available_uids if uid not in selected_uids]

    bt.logging.info(
        f"Selected {len(selected_uids)} unique uncalled UIDs, {len(remaining_uncalled)} uncalled UIDs remaining"
    )

    return selected_uids
