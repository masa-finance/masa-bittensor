import os
import requests
import bittensor as bt
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.discord import DiscordProfileObject


class DiscordProfileRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()

    def get_profile(self, user_id) -> DiscordProfileObject:
        bt.logging.info(f"Getting profile from worker {user_id}")
        response = self.get(f"/data/discord/profile/{user_id}")

        response_json = response.json()

        if "error" in response_json:
            error_message = response_json["error"]
            bt.logging.error(f"Error fetching profile: {error_message}")
            return None

        discord_profile = self.format_profile(response_json)

        return discord_profile

    def format_profile(self, data: requests.Response) -> DiscordProfileObject:
        bt.logging.info(f"Formatting discord profile data: {data}")
        profile_data = data["data"]
        discord_profile = DiscordProfileObject(**profile_data)

        return discord_profile
