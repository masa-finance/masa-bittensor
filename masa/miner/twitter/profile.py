import bittensor as bt
from typing import List
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import TwitterProfileObject
from masa.synapses import TwitterProfileSynapse


def handle_twitter_profile(synapse: TwitterProfileSynapse) -> TwitterProfileSynapse:
    synapse.response = TwitterProfileRequest().get_profile(synapse)
    return synapse


class TwitterProfileRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()

    def get_profile(self, synapse: TwitterProfileSynapse) -> List[TwitterProfileObject]:
        bt.logging.info(f"Getting profile for: {synapse}")
        response = self.get(f"/data/twitter/profile/{synapse.username}")
        if response.ok:
            data = self.format(response)
            return data
        else:
            bt.logging.error(
                f"Twitter profile request failed with status code: {response.status_code}"
            )
            return None
