import bittensor as bt
from typing import Optional, Any


class RecentTweetsSynapse(bt.Synapse):
    query: str
    count: Optional[int] = None
    response: Optional[Any] = None
    timeout: Optional[int] = 10

    def deserialize(self) -> Optional[Any]:
        return self.response


class TwitterProfileSynapse(bt.Synapse):
    username: str
    response: Optional[Any] = None

    def deserialize(self) -> Any:
        return self.response


class TwitterFollowersSynapse(bt.Synapse):
    username: str
    count: int
    response: Optional[Any] = None

    def deserialize(self) -> Any:
        return self.response


class PingAxonSynapse(bt.Synapse):
    sent_from: Optional[str]
    is_active: Optional[bool]
    version: Optional[int]

    def deserialize(self) -> int:
        return self.version
