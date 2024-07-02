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


class TwitterFollowerObject(TypedDict, total=False):
    can_dm: Optional[bool]
    can_media_tag: Optional[bool]
    created_at: Optional[str]
    default_profile: Optional[bool]
    default_profile_image: Optional[bool]
    description: Optional[str]
    entities: Optional[
        dict
    ]  # This could be further detailed with a TypedDict if necessary
    fast_followers_count: Optional[int]
    favourites_count: Optional[int]
    followers_count: Optional[int]
    friends_count: Optional[int]
    has_custom_timelines: Optional[bool]
    is_translator: Optional[bool]
    listed_count: Optional[int]
    location: Optional[str]
    media_count: Optional[int]
    name: Optional[str]
    normal_followers_count: Optional[int]
    pinned_tweet_ids_str: Optional[List[str]]
    possibly_sensitive: Optional[bool]
    profile_banner_url: Optional[str]
    profile_image_url_https: Optional[str]
    screen_name: Optional[str]
    statuses_count: Optional[int]
    translator_type: Optional[str]
    url: Optional[str]
    verified: Optional[bool]
    want_retweets: Optional[bool]
    withheld_in_countries: Optional[List[str]]


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
