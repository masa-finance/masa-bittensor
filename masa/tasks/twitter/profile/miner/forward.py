
import bittensor as bt

from masa.tasks.twitter.profile.miner.request import TwitterProfileRequest
from masa.tasks.twitter.profile.protocol import TwitterProfileProtocol

def forward_twitter_profile(synapse: TwitterProfileProtocol) -> TwitterProfileProtocol:
    profile = TwitterProfileRequest().get_profile(synapse.query)
    if profile != None:
        profile_dict = dict(profile)
        synapse.response = profile_dict
    else:
        bt.logging.error(f"Failed to fetch Twitter profile for {synapse.query}.")
        
        
    return synapse