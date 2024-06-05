from dataclasses import dataclass
import requests
import bittensor as bt
from typing import List
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import TwitterTweetObject

@dataclass
class RecentTweetsQuery:
    query: str
    count: int

class TwitterTweetsRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()


    def get_recent_tweets(self, query: RecentTweetsQuery) -> List[TwitterTweetObject]:
        bt.logging.info(f"Getting recent tweets from worker with query: {query}")
        response = self.post(f"/data/twitter/tweets/recent", body={"query": query.query, "count": query.count})
        
        if response.status_code == 504:
            bt.logging.error("Worker request failed")
            return None
        tweets = self.format_tweets(response)
        return tweets
        
        
    def format_tweets(self, data: requests.Response) -> List[TwitterTweetObject]:
        bt.logging.info(f"Formatting twitter tweets data: {data}")
        tweets_data = data.json()['data']
        twitter_tweets = [
            TwitterTweetObject(**tweet) for tweet in tweets_data
        ]
        
        return twitter_tweets
            
