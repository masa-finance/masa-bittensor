from typing import Optional, List, Dict
from typing_extensions import TypedDict

class DiscordProfileObject(TypedDict):
    ID: str
    Username: str
    Discriminator: str
    Avatar: str

class DiscordChannelMessageObject(TypedDict):
    ID: str
    ChannelID: str
    Author: DiscordProfileObject
    Content: str
    Timestamp: str

class DiscordGuildChannelObject(TypedDict):
    ID: str
    GuildID: str
    Name: str
    Type: int

class DiscordGuildObject(TypedDict):
    ID: str
    Name: str
    Icon: str
    Owner: bool
    Permissions: int