import bittensor as bt
from enum import Enum
from typing import Optional, Any

class RequestType(Enum):
    TWITTER_PROFILE = "twitter_profile"
    TWITTER_FOLLOWERS = "twitter_followers"
    TWITTER_TWEETS = "twitter_tweets"
    WEB_SCRAPER = "web_scraper"

class Request(bt.Synapse):
    query: str
    type: str
    url: Optional[str] = None
    depth: Optional[int] = None
    count: Optional[int] = None
    response: Optional[Any] = None


    def deserialize(self) -> int:
        return self.response