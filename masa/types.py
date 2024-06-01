from typing import Optional, List
from typing_extensions import TypedDict
class TwitterObject(TypedDict, total=False):
    UserID: str
    Avatar: Optional[str]
    Banner: Optional[str]
    Biography: Optional[str]
    Birthday: Optional[str]
    FollowersCount: Optional[int]
    FollowingCount: Optional[int]
    FriendsCount: Optional[int]
    IsPrivate: Optional[bool]
    IsVerified: Optional[bool]
    Joined: Optional[str]
    LikesCount: Optional[int]
    ListedCount: Optional[int]
    Location: Optional[str]
    Name: Optional[str]
    PinnedTweetIDs: Optional[List[str]]
    TweetsCount: Optional[int]
    URL: Optional[str]
    Username: Optional[str]
    Website: Optional[str]
