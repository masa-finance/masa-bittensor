import os
import requests
import bittensor as bt
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.discord import DiscordProfileObject

class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

class DiscordProfileRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()
    
    def get_profile(self, user_id) -> DiscordProfileObject:
        bt.logging.info(f"Getting profile from worker {user_id}")
        # response = self.get(f"/data/discord/profile/{user_id}")
        response = MockResponse({
            "data": {
                "ID": user_id,
                "Username": "name",
                "Discriminator": "disc",
                "Avatar": "avatar"
            }
        }, 200)
        
        if response.status_code == 504:
            bt.logging.error("Worker request failed")
            return None
        discord_profile = self.format_profile(response)
        
        return discord_profile
        
    def format_profile(self, data: requests.Response) -> DiscordProfileObject:
        bt.logging.info(f"Formatting discord profile data: {data}")
        profile_data = data.json()['data']
        discord_profile = DiscordProfileObject(**profile_data)
        
        return discord_profile
