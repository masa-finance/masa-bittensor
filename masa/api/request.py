import typing
import bittensor as bt
from ..types.twitter import TwitterProfileObject 
from typing import Optional

class Request(bt.Synapse):
    request: str
    twitter_object: Optional[TwitterProfileObject] = None


    def deserialize(self) -> int:
        return self.twitter_object