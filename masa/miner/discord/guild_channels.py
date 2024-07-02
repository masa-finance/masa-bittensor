import requests
import bittensor as bt
from typing import List
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.discord import DiscordGuildChannelObject


class DiscordGuildChannelsRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()

    def get_discord_guild_channels(self, guild_id) -> List[DiscordGuildChannelObject]:
        bt.logging.info(f"Getting guild channels from worker {guild_id}")

        response = self.get(f"/data/discord/guilds/{guild_id}/channels")

        response_json = response.json()

        if "error" in response_json:
            bt.logging.error("Worker request failed")
            return None

        discord_guild_channels = self.format_guild_channels(response_json)

        return discord_guild_channels

    def format_guild_channels(
        self, data: requests.Response
    ) -> List[DiscordGuildChannelObject]:
        bt.logging.info(f"Formatting discord guild channels data: {data}")
        guild_channels_data = data["data"]
        discord_guild_channels = [
            DiscordGuildChannelObject(**channel_message)
            for channel_message in guild_channels_data
        ]
        return discord_guild_channels
