import requests
import bittensor as bt
from typing import List
from masa.miner.protocol import ProtocolRequest
from masa.types.twitter import TwitterTweetObject

class TwitterTweetsRequest(ProtocolRequest):
    def __init__(self):
        super().__init__()


    def get_tweets(self, query) -> List[TwitterTweetObject]:
        bt.logging.info(f"Getting recent tweets from worker with query: {query}")
        response = self.post(f"/data/twitter/tweets/recent", body={"query": query, "count": 10})
        
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
            
