import requests
import bittensor as bt
from typing import List
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.discord import DiscordGuildObject

class DiscordAllGuildsRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()
    
    def get_discord_all_guilds(self) -> List[DiscordGuildObject]:
        bt.logging.info(f"Getting all guilds from worker")

        response = self.get("/data/discord/guilds/all")

        response_data = response.json()
        print(response_data)
        
        if response.status_code == 504:
            bt.logging.error("Worker request failed")
            return None
        discord_all_guilds = self.format_all_guilds(response_data)

        return discord_all_guilds

    def format_all_guilds(self, data: requests.Response) -> List[DiscordGuildObject]:
        bt.logging.info(f"Formatting discord all guilds data: {data}")
        guild_channels_data = data['guilds']
        discord_all_guilds = [
            DiscordGuildObject(**guild) for guild in guild_channels_data
        ]        
        return discord_all_guilds
