from dataclasses import dataclass
import requests
import bittensor as bt
from typing import List, Optional, Any
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import ProtocolTwitterTweetResponse


@dataclass
class RecentTweetsQuery:
    query: str
    count: int


# note, this is currently needed so that we don't override the forward method...
class PingVolume(bt.Synapse):
    query: Optional[str]
    count: Optional[int]
    response: Optional[Any] = None

    def deserialize(self) -> Any:
        return self.response


def forward_volume(synapse: PingVolume) -> PingVolume:
    response = TwitterTweetsRequest().get_recent_tweets(synapse)
    synapse.response = response
    return synapse


class TwitterTweetsRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()

    def get_recent_tweets(
        self, synapse: PingVolume
    ) -> List[ProtocolTwitterTweetResponse]:
        bt.logging.info(f"Getting recent tweets from worker with query: {synapse}")
        response = self.post(
            "/data/twitter/tweets/recent",
            body={"query": synapse.query, "count": synapse.count},
        )
        if response.ok:
            data = self.format(response)
            return data
        else:
            bt.logging.error(
                f"Worker request failed with response: {response.status_code}"
            )
            return None
