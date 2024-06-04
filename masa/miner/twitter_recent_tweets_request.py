import os
import requests
import bittensor as bt
from typing import List
from masa.types.twitter import TwitterTweetObject

class TwitterRecentTweetsRequest():
    def __init__(self):
        self.base_url = os.getenv('BASE_URL', "http://localhost:8080/api/v1")
        self.authorization = os.getenv('AUTHORIZATION', "Bearer 1234")
        self.headers = {"Authorization": self.authorization, "Content-Type": "application/json"}
        
    def post(self, path, body) -> requests.Response:
        timeout_duration = 1
        return requests.post(f"{self.base_url}{path}", json=body, headers=self.headers, timeout=timeout_duration)
    
    def get_recent_tweets(self, query: str, count: int) -> List[TwitterTweetObject]:
        bt.logging.info(f"Fetching recent tweets with query: {query} and count: {count}")
        body = {"query": query, "count": count}
        response = self.post("/data/twitter/tweets/recent", body)
        
        if response.status_code == 504:
            bt.logging.error("Worker request failed")
            return []
        tweets = self.format_tweets(response)
        
        return tweets
        
    def format_tweets(self, data: requests.Response) -> List[TwitterTweetObject]:
        bt.logging.info(f"Formatting twitter tweets data: {data}")
        tweets_data = data.json()['data']
        tweets = [TwitterTweetObject(**tweet) for tweet in tweets_data]
        
        return tweets