from dataclasses import dataclass
import requests
import bittensor as bt
from typing import List
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import ProtocolTwitterTweetResponse


@dataclass
class RecentTweetsQuery:
    query: str
    count: int


class TwitterTweetsRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()

    def get_recent_tweets(
        self, query: RecentTweetsQuery
    ) -> List[ProtocolTwitterTweetResponse]:
        bt.logging.info(f"Getting recent tweets from worker with query: {query}")
        response = self.post(
            "/data/twitter/tweets/recent",
            body={"query": query.query, "count": query.count},
        )
        if response.ok:
            tweets = self.format(response)
            return tweets
        else:
            bt.logging.error(
                f"Worker request failed with response: {response.status_code}"
            )
            return None
