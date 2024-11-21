import bittensor as bt
from typing import List
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import TwitterFollowerObject
from masa.synapses import TwitterFollowersSynapse


def handle_twitter_followers(
    synapse: TwitterFollowersSynapse,
) -> TwitterFollowersSynapse:
    synapse.response = TwitterFollowersRequest().get_followers(synapse)
    return synapse


class TwitterFollowersRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()

    def get_followers(
        self, synapse: TwitterFollowersSynapse
    ) -> List[TwitterFollowerObject]:
        bt.logging.info(
            f"Getting {synapse.count} twitter followers for: {synapse.username}"
        )
        response = self.get(
            f"/data/twitter/followers/{synapse.username}?limit={synapse.count}"
        )
        if response.ok:
            data = self.format(response)
            return data
        else:
            bt.logging.error(
                f"Twitter followers request failed with status code: {response.status_code}"
            )
            return None
