import bittensor as bt
from typing import Optional, Any

class TwitterProfileProtocol(bt.Synapse):
    query: Optional[str] = None
    response: Optional[Any] = None

    def deserialize(self) -> int:
        return self.response