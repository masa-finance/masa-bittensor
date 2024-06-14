import requests
import bittensor as bt
from typing import List
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.discord import DiscordGuildObject

class DiscordUserGuildsRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()
    
    def get_discord_user_guilds(self) -> List[DiscordGuildObject]:
        bt.logging.info(f"Getting user guilds from worker")

        response = self.get("/data/discord/user/guilds")

        response_data = response.json()
        print(response_data)
        
        if response.status_code == 504:
            bt.logging.error("Worker request failed")
            return None
        discord_user_guilds = self.format_user_guilds(response_data)

        print(discord_user_guilds)
        
        return discord_user_guilds

    def format_user_guilds(self, data: requests.Response) -> List[DiscordGuildObject]:
        bt.logging.info(f"Formatting discord user guilds data: {data}")
        guild_channels_data = data['data']
        discord_user_guilds = [
            DiscordGuildObject(**user_guild) for user_guild in guild_channels_data
        ]        
        return discord_user_guilds
