import requests
import bittensor as bt
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import TwitterProfileObject


class TwitterProfileRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()

    def get_profile(self, profile) -> TwitterProfileObject:
        bt.logging.info(f"Getting profile from worker {profile}")
        response = self.get(f"/data/twitter/profile/{profile}")
        if response.ok:
            data = self.format(response)
            return data
        else:
            bt.logging.error(
                f"Worker request failed with response: {response.status_code}"
            )
            return None
