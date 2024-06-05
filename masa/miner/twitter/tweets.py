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
            TwitterTweetObject(
                ConversationID=tweet.get("ConversationID", None),
                GIFs=tweet.get("GIFs", None),
                HTML=tweet.get("HTML", None),
                Hashtags=tweet.get("Hashtags", None),
                ID=tweet.get("ID", None),
                InReplyToStatus=tweet.get("InReplyToStatus", None),
                InReplyToStatusID=tweet.get("InReplyToStatusID", None),
                IsPin=tweet.get("IsPin", False),
                IsQuoted=tweet.get("IsQuoted", False),
                IsReply=tweet.get("IsReply", False),
                IsRetweet=tweet.get("IsRetweet", False),
                IsSelfThread=tweet.get("IsSelfThread", False),
                Likes=tweet.get("Likes", 0),
                Mentions=tweet.get("Mentions", None),
                Name=tweet.get("Name", None),
                PermanentURL=tweet.get("PermanentURL", None),
                Photos=tweet.get("Photos", None),
                Place=tweet.get("Place", None),
                QuotedStatus=tweet.get("QuotedStatus", None),
                QuotedStatusID=tweet.get("QuotedStatusID", None),
                Replies=tweet.get("Replies", 0),
                RetweetedStatus=tweet.get("RetweetedStatus", None),
                RetweetedStatusID=tweet.get("RetweetedStatusID", None),
                Retweets=tweet.get("Retweets", 0),
                SensitiveContent=tweet.get("SensitiveContent", False),
                Text=tweet.get("Text", None),
                Thread=tweet.get("Thread", None),
                TimeParsed=tweet.get("TimeParsed", None),
                Timestamp=tweet.get("Timestamp", 0),
                URLs=tweet.get("URLs", None),
                UserID=tweet.get("UserID", None),
                Username=tweet.get("Username", None),
                Videos=tweet.get("Videos", None),
                Views=tweet.get("Views", 0)
            ) for tweet in tweets_data
        ]
        
        return twitter_tweets
            
