from typing import Optional, List, Dict
from typing_extensions import TypedDict

class DiscordProfileObject(TypedDict):
    ID: str
    Username: str
    Discriminator: str
    Avatar: str