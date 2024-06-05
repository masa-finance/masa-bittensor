import requests
import bittensor as bt
from typing import List
from masa.miner.protocol import ProtocolRequest
from masa.types.twitter import TwitterFollowerObject

class TwitterFollowersRequest(ProtocolRequest):
    def __init__(self):
        super().__init__()


    def get_followers(self, username) -> List[TwitterFollowerObject]:
        bt.logging.info(f"Getting followers from worker {username}")
        response = self.get(f"/data/twitter/followers/{username}")
        
        if response.status_code == 504:
            bt.logging.error("Worker request failed")
            return None
        twitter_followers = self.format_followers(response)
        
        return twitter_followers
        
        
    def format_followers(self, data: requests.Response) -> List[TwitterFollowerObject]:
        bt.logging.info(f"Formatting twitter followers data: {data}")
        followers_data = data.json()['data']
        twitter_followers = [
            TwitterFollowerObject(
                can_dm=follower.get("can_dm", None),
                can_media_tag=follower.get("can_media_tag", None),
                created_at=follower.get("created_at", None),
                default_profile=follower.get("default_profile", None),
                default_profile_image=follower.get("default_profile_image", None),
                description=follower.get("description", None),
                entities=follower.get("entities", None),
                fast_followers_count=follower.get("fast_followers_count", None),
                favourites_count=follower.get("favourites_count", None),
                followers_count=follower.get("followers_count", None),
                friends_count=follower.get("friends_count", None),
                has_custom_timelines=follower.get("has_custom_timelines", None),
                is_translator=follower.get("is_translator", None),
                listed_count=follower.get("listed_count", None),
                location=follower.get("location", None),
                media_count=follower.get("media_count", None),
                name=follower.get("name", None),
                normal_followers_count=follower.get("normal_followers_count", None),
                pinned_tweet_ids_str=follower.get("pinned_tweet_ids_str", None),
                possibly_sensitive=follower.get("possibly_sensitive", None),
                profile_banner_url=follower.get("profile_banner_url", None),
                profile_image_url_https=follower.get("profile_image_url_https", None),
                screen_name=follower.get("screen_name", None),
                statuses_count=follower.get("statuses_count", None),
                translator_type=follower.get("translator_type", None),
                url=follower.get("url", None),
                verified=follower.get("verified", None),
                want_retweets=follower.get("want_retweets", None),
                withheld_in_countries=follower.get("withheld_in_countries", None)
            ) for follower in followers_data
        ]
        
        return twitter_followers
            
