import bittensor as bt
from typing import List, Optional
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import ProtocolTwitterTweetResponse
from masa.synapses import RecentTweetsSynapse
import json


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
        bt.logging.info(f"Getting recent tweets for: {synapse.query}")
        query = synapse.query
        file_path = f"{query}.json"
        bt.logging.info(f"validator requesting tweets for {query}...")

        # load stored tweets...
        try:
            with open(file_path, "r") as json_file:
                stored_tweets = json.load(json_file)
            bt.logging.info(f"loaded {len(stored_tweets)} tweets from {file_path}...")
        except FileNotFoundError:
            bt.logging.warning(f"no existing file for {file_path}")
            stored_tweets = []

        bt.logging.success(f"Sending {len(stored_tweets)} tweets to validator...")
        return stored_tweets
