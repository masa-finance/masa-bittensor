import requests
import bittensor as bt
from typing import List
from masa.miner.protocol import ProtocolRequest
from masa.types.twitter import TwitterFollowerObject

class TwitterFollowersRequest(ProtocolRequest):
    def __init__(self):
        super().__init__()


    def get_followers(self, username) -> List[TwitterFollowerObject]:
        bt.logging.info(f"Getting followers from worker {username}")
        response = self.get(f"/data/twitter/followers/{username}")
        
        if response.status_code == 504:
            bt.logging.error("Worker request failed")
            return None
        twitter_followers = self.format_followers(response)
        
        return twitter_followers
        
        
    def format_followers(self, data: requests.Response) -> List[TwitterFollowerObject]:
        bt.logging.info(f"Formatting twitter followers data: {data}")
        followers_data = data.json()['data']
        twitter_followers = [
            TwitterFollowerObject(**follower) for follower in followers_data
        ]
        
        return twitter_followers
            
