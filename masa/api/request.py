import typing
import bittensor as bt
from ..types import TwitterObject
from typing import Optional

class Request(bt.Synapse):
    request: str
    twitter_object: Optional[TwitterObject] = None


    def deserialize(self) -> int:
        return self.twitter_object