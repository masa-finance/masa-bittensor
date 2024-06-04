from typing import Optional, List, Dict
from typing_extensions import TypedDict
class TwitterProfileObject(TypedDict, total=False):
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

class TwitterTweetObject(TypedDict, total=False):
    ConversationID: str
    GIFs: Optional[List[str]]
    HTML: str
    Hashtags: Optional[List[str]]
    ID: str
    InReplyToStatus: Optional[Dict]
    InReplyToStatusID: Optional[str]
    IsPin: bool
    IsQuoted: bool
    IsReply: bool
    IsRetweet: bool
    IsSelfThread: bool
    Likes: int
    Mentions: Optional[List[Dict[str, str]]]
    Name: str
    PermanentURL: str
    Photos: Optional[List[str]]
    Place: Optional[str]
    QuotedStatus: Optional[Dict]
    QuotedStatusID: Optional[str]
    Replies: int
    RetweetedStatus: Optional[Dict]
    RetweetedStatusID: Optional[str]
    Retweets: int
    SensitiveContent: bool
    Text: str
    Thread: Optional[List[str]]
    TimeParsed: str
    Timestamp: int
    URLs: Optional[List[str]]
    UserID: str
    Username: str
    Videos: Optional[List[str]]
    Views: int