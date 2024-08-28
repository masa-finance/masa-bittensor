import requests
import bittensor as bt
from typing import List
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import TwitterFollowerObject


class TwitterFollowersRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()

    def get_followers(self, username) -> List[TwitterFollowerObject]:
        bt.logging.info(f"Getting followers from worker {username}")
        response = self.get(f"/data/twitter/followers/{username}")
        if response.ok:
            data = self.format(response)
            return data
        else:
            bt.logging.error(
                f"Worker request failed with response: {response.status_code}"
            )
            return None
