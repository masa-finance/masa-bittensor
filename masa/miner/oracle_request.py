import requests
import bittensor as bt
from masa.types.twitter import TwitterProfileObject

class OracleRequest():
    def __init__(self):
        self.base_url = "http://localhost:8080/api/v1"
        self.authorization = "Bearer 1234"
        self.headers = {"Authorization": self.authorization }
        
    def get(self, path) -> requests.Response:
        return requests.get(f"{self.base_url}{path}", headers=self.headers)
    
    def get_profile(self, profile) -> TwitterProfileObject:
        bt.logging.info(f"Getting profile from oracle {profile}")
        response = self.get(f"/data/twitter/profile/{profile}")
        
        if response.status_code == 504:
            bt.logging.error("Oracle request failed")
            return None
        twitter_profile = self.format_profile(response)
        
        return twitter_profile
        
    def format_profile(self, data: requests.Response) -> TwitterProfileObject:
        bt.logging.info(f"Formatting oracle data: {data}")
        profile_data = data.json()['data']
        twitter_profile = TwitterProfileObject(
                    UserID=profile_data.get("UserID", None),
                    Avatar=profile_data.get("Avatar", None),
                    Banner=profile_data.get("Banner", None),
                    Biography=profile_data.get("Biography", None),
                    Birthday=profile_data.get("Birthday", None),
                    FollowersCount=profile_data.get("FollowersCount", None),
                    FollowingCount=profile_data.get("FollowingCount", None),
                    FriendsCount=profile_data.get("FriendsCount", None),
                    IsPrivate=profile_data.get("IsPrivate", None),
                    IsVerified=profile_data.get("IsVerified", None),
                    Joined=profile_data.get("Joined", None),
                    LikesCount=profile_data.get("LikesCount", None),
                    ListedCount=profile_data.get("ListedCount", None),
                    Location=profile_data.get("Location", None),
                    Name=profile_data.get("Name", None),
                    PinnedTweetIDs=profile_data.get("PinnedTweetIDs", None),
                    TweetsCount=profile_data.get("TweetsCount", None),
                    URL=profile_data.get("URL", None),
                    Username=profile_data.get("Username", None),
                    Website=profile_data.get("Website", None)
                )
        
        return twitter_profile
            

