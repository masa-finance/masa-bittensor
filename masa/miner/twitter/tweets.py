import bittensor as bt
from typing import List, Optional
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import ProtocolTwitterTweetResponse
from masa.synapses import RecentTweetsSynapse
import requests


def handle_recent_tweets(synapse: RecentTweetsSynapse, max: int) -> RecentTweetsSynapse:
    synapse.response = TwitterTweetsRequest(max).get_recent_tweets(synapse)
    return synapse


class TwitterTweetsRequest(MasaProtocolRequest):
    def __init__(self, max_tweets: int):
        super().__init__()
        # note, the max is determined by the miner config --twitter.max_tweets_per_request
        self.max_tweets = min(max_tweets, 900)  # twitter's limit per request

    def get_recent_tweets(
        self, synapse: RecentTweetsSynapse
    ) -> Optional[List[ProtocolTwitterTweetResponse]]:
        bt.logging.info(
            f"Getting {synapse.count or self.max_tweets} recent tweets for: {synapse.query}"
        )
        try:
            response = self.post(
                "/data/twitter/tweets/recent",
                body={
                    "query": synapse.query,
                    "count": synapse.count or self.max_tweets,
                },
                timeout=synapse.timeout,
            )
            if response.ok:
                data = self.format(response)
                bt.logging.success(f"Sending {len(data)} tweets to validator...")
                return data
            else:
                bt.logging.error(
                    f"Recent tweets request failed with status code: {response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            bt.logging.error(f"Recent tweets request failed: {e}")
