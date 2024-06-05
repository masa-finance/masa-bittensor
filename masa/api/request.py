import bittensor as bt
from enum import Enum
# from ..types.twitter import TwitterProfileObject 
from typing import Optional, Any

class RequestType(Enum):
    TWITTER_PROFILE = "twitter_profile"
    TWITTER_FOLLOWERS = "twitter_followers"
    TWITTER_TWEETS_RECENT = "twitter_tweets_recent"

class Request(bt.Synapse):
    request: str
    type: str
    response: Optional[Any] = None


    def deserialize(self) -> int:
        return self.response