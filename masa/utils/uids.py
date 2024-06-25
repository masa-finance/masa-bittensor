import torch
import random
import bittensor as bt
from typing import List


def check_uid_availability(
    metagraph: "bt.metagraph.Metagraph", uid: int, vpermit_tao_limit: int
) -> bool:
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
        return False

    # Filter out non validator permit.
    if metagraph.validator_permit[uid]:

        # Filter out neurons who are validators
        if metagraph.S[uid] > vpermit_tao_limit:
            return False

        # Filter out uid without IP.
        if metagraph.neurons[uid].axon_info.ip == "0.0.0.0":
            return False

    # Available otherwise.
    return True


def get_available_uids(
    metagraph: "bt.metagraph.Metagraph", vpermit_tao_limit: int
) -> List[int]:
    return [
        uid
        for uid in range(metagraph.n.item())
        if check_uid_availability(metagraph, uid, vpermit_tao_limit)
    ]


def remove_excluded_uids(uids: List[int], exclude: List[int]) -> List[int]:
    return [uid for uid in uids if uid not in exclude]


async def ping_uids(dendrite, metagraph, uids, timeout=3):
    """
    Pings a list of UIDs to check their availability on the Bittensor network.

    Args:
        dendrite (bittensor.dendrite): The dendrite instance to use for pinging nodes.
        metagraph (bittensor.metagraph): The metagraph instance containing network information.
        uids (list): A list of UIDs (unique identifiers) to ping.
        timeout (int, optional): The timeout in seconds for each ping. Defaults to 3.

    Returns:
        tuple: A tuple containing two lists:
            - The first list contains UIDs that were successfully pinged.
            - The second list contains UIDs that failed to respond.
    """
    axons = [metagraph.axons[uid] for uid in uids]
    try:
        responses = await dendrite(
            axons,
            bt.Synapse(),  # TODO: potentially get the synapses available back?
            deserialize=False,
            timeout=timeout,
        )
        successful_uids = [
            uid
            for uid, response in zip(uids, responses)
            if response.dendrite.status_code == 200
        ]
        failed_uids = [
            uid
            for uid, response in zip(uids, responses)
            if response.dendrite.status_code != 200
        ]
    except Exception as e:
        bt.logging.error(f"Dendrite ping failed: {e}")
        successful_uids = []
        failed_uids = uids
    bt.logging.debug(f"ping() successful uids: {successful_uids}")
    bt.logging.debug(f"ping() failed uids    : {failed_uids}")
    return successful_uids, failed_uids


def filter_duplicated_axon_ips_for_uids(uids, metagraph):
    ips = []
    miner_ip_filtered_uids = []
    for uid in uids:
        if metagraph.axons[uid].ip not in ips:
            ips.append(metagraph.axons[uid].ip)
            miner_ip_filtered_uids.append(uid)
    return miner_ip_filtered_uids


def get_random_uids(self, k: int, exclude: List[int] = None) -> torch.LongTensor:
    """Returns k available random uids from the metagraph.
    Args:
        k (int): Number of uids to return.
        exclude (List[int]): List of uids to exclude from the random sampling.
    Returns:
        uids (torch.LongTensor): Randomly sampled available uids.
    Notes:
        If `k` is larger than the number of available `uids`, set `k` to the number of available `uids`.
    """
    candidate_uids = []
    avail_uids = []

    print("get random uids")

    avail_uids = get_available_uids(
        self.metagraph, self.config.neuron.vpermit_tao_limit
    )
    candidate_uids = remove_excluded_uids(avail_uids, exclude)
    # If k is larger than the number of available uids, set k to the number of available uids.
    k = min(k, len(avail_uids))
    # Check if candidate_uids contain enough for querying, if not grab all avaliable uids
    available_uids = candidate_uids

    print("AVAIL UIDS: ", avail_uids)
    if len(candidate_uids) < k:
        available_uids += random.sample(
            [uid for uid in avail_uids if uid not in candidate_uids],
            k - len(candidate_uids),
        )

    print("AVAILABLE UIDS: ", available_uids)

    random_sample = random.sample(available_uids, k)
    print(f"Random sample: {random_sample}")
    uids = torch.tensor(random_sample)
    return uids
