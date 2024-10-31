import bittensor as bt
from typing import List, Optional, Any
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import ProtocolTwitterTweetResponse


# TODO we can refactor this to synapses directory, as both vali and miner use
class RecentTweetsSynapse(bt.Synapse):
    query: str
    count: Optional[int] = None
    response: Optional[Any] = None

    def deserialize(self) -> Optional[Any]:
        return self.response


def forward_recent_tweets(
    synapse: RecentTweetsSynapse, max: int
) -> RecentTweetsSynapse:
    synapse.response = TwitterTweetsRequest(max).get_recent_tweets(synapse)
    return synapse


class TwitterTweetsRequest(MasaProtocolRequest):
    def __init__(self, max_tweets: int):
        super().__init__()
        # note, this value is max tweets per request for synthetic scoring
        self.max_tweets = max_tweets

    def get_recent_tweets(
        self, synapse: RecentTweetsSynapse
    ) -> Optional[List[ProtocolTwitterTweetResponse]]:
        bt.logging.info(
            f"Getting {synapse.count or self.max_tweets} recent tweets for: {synapse.query}"
        )
        response = self.post(
            "/data/twitter/tweets/recent",
            body={"query": synapse.query, "count": synapse.count or self.max_tweets},
        )
        if response.ok:
            data = self.format(response)
            bt.logging.success(f"Sending {len(data)} tweets to validator...")
            return data
        else:
            bt.logging.error(
                f"Twitter recent tweets request failed with status code: {response.status_code}"
            )
            return None
