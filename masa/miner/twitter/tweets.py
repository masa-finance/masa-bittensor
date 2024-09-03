import bittensor as bt
from typing import List, Optional, Any
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import ProtocolTwitterTweetResponse


class RecentTweetsSynapse(bt.Synapse):
    query: str
    count: int
    response: Optional[Any] = None

    def deserialize(self) -> Optional[Any]:
        return self.response


def forward_recent_tweets(synapse: RecentTweetsSynapse) -> RecentTweetsSynapse:
    synapse.response = TwitterTweetsRequest().get_recent_tweets(synapse)
    return synapse


class TwitterTweetsRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()

    def get_recent_tweets(
        self, synapse: RecentTweetsSynapse
    ) -> Optional[List[ProtocolTwitterTweetResponse]]:
        bt.logging.info(f"Getting {synapse.count} recent tweets for: {synapse.query}")
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
