import requests
import bittensor as bt
from masa.api.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import TwitterProfileObject

class TwitterProfileRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()
    
    def get_profile(self, profile) -> TwitterProfileObject:
        bt.logging.info(f"Getting profile from worker {profile}")
        response = self.get(f"/data/twitter/profile/{profile}")
        
        if response.status_code == 504:
            bt.logging.error("Worker request failed")
            return None
        twitter_profile = self.format_profile(response)
        
        return twitter_profile
        
    def format_profile(self, data: requests.Response) -> TwitterProfileObject:
        bt.logging.info(f"Formatting twitter profile data: {data}")
        profile_data = data.json()['data']
        twitter_profile = TwitterProfileObject(**profile_data)
        
        return twitter_profile
            

