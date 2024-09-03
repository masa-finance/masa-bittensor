import os
import asyncio
import uvicorn
import bittensor as bt
from typing import Any
from datetime import datetime

from masa.miner.twitter.tweets import RecentTweetsSynapse
from masa.miner.twitter.profile import TwitterProfileSynapse
from masa.miner.twitter.followers import TwitterFollowersSynapse

from masa.base.validator import get_random_miner_uids

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


TIMEOUT = 8


class ValidatorAPI:
    def __init__(self, validator, config=None):
        self.host = os.getenv("VALIDATOR_API_HOST", "0.0.0.0")
        self.port = int(os.getenv("VALIDATOR_API_PORT", "8000"))
        self.validator = validator
        self.app = FastAPI()

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.app.add_api_route(
            "/score",
            validator.scorer.score_miner_volumes,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Score miner volumes",
            tags=["scoring"],
        )

        self.app.add_api_route(
            "/volumes",
            self.show_volumes,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get scores and capacity of miners",
            tags=["scoring"],
        )

        self.app.add_api_route(
            "/data/twitter/profile",
            self.get_twitter_profile,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the Twitter profile for the given username",
            tags=["twitter"],
        )

        self.app.add_api_route(
            "/data/twitter/followers",
            self.get_twitter_followers,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the Twitter followers for the given username",
            tags=["twitter"],
        )

        self.app.add_api_route(
            "/data/twitter/tweets/recent",
            self.get_recent_tweets,
            methods=["POST"],
            dependencies=[Depends(self.get_self)],
            response_description="Get recent tweets given a query",
            tags=["twitter"],
        )

        self.app.add_api_route(
            "/data/discord/profile/{user_id}",
            self.get_discord_profile,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the Discord profile for the given user ID",
            tags=["discord"],
        )

        self.app.add_api_route(
            "/data/discord/channels/{channel_id}/messages",
            self.get_discord_channel_messages,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the Discord channel messages for the given channel ID",
            tags=["discord"],
        )

        self.app.add_api_route(
            "/data/discord/guilds/{guild_id}/channels",
            self.get_discord_guild_channels,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the Discord channels for the given guild ID",
            tags=["discord"],
        )

        self.app.add_api_route(
            "/data/discord/user/guilds",
            self.get_discord_user_guilds,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the Discord guilds for the user",
            tags=["discord"],
        )

        self.app.add_api_route(
            "/data/discord/guilds/all",
            self.get_discord_all_guilds,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get all guilds that all the Discord workers are apart of",
            tags=["discord"],
        )

        self.app.add_api_route(
            "/axons",
            self.get_axons,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the axons for the given metagraph",
            tags=["metagraph"],
        )
        self.app.add_api_route(
            "/healthcheck",
            self.healthcheck,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get healthcheck status",
            tags=["metagraph"],
        )
        self.app.add_api_route(
            "/versions",
            self.get_miners_versions,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get miners versions",
            tags=["metagraph"],
        )

        self.start_server()

    async def show_volumes(self):
        volumes = self.validator.volumes
        if volumes:
            # Convert all elements in volumes to a JSON serializable format
            serializable_volumes = [
                {
                    "block_group": int(volume["block_group"]),
                    "miners": {int(k): float(v) for k, v in volume["miners"].items()},
                }
                for volume in volumes
            ]
            return JSONResponse(content=serializable_volumes)
        return JSONResponse(content=[])

    async def get_miners_versions(self):
        versions = await self.validator.get_miner_versions()
        if versions:
            return versions
        return []

    async def send_dendrite_request(self, request: Any):
        miner_uids = await get_random_miner_uids(
            self.validator, k=self.validator.config.neuron.sample_size
        )
        dendrite = bt.dendrite(wallet=self.validator.wallet)
        responses = await dendrite(
            [self.validator.metagraph.axons[uid] for uid in miner_uids],
            request,
            deserialize=True,
            timeout=TIMEOUT,
        )

        formatted_responses = [
            {"uid": int(uid), "response": response}
            for uid, response in zip(miner_uids, responses)
        ]
        return formatted_responses

    async def get_twitter_profile(self, username: str = "getmasafi"):
        request = TwitterProfileSynapse(username=username)
        return await self.send_dendrite_request(request)

    async def get_twitter_followers(self, username: str = "getmasafi", count: int = 10):
        request = TwitterFollowersSynapse(username=username, count=count)
        return await self.send_dendrite_request(request)

    async def get_recent_tweets(
        self,
        query: str = f"(Bitcoin) since:{datetime.now().strftime('%Y-%m-%d')}",
        count: int = 1,
    ):
        request = RecentTweetsSynapse(query=query, count=count)
        return await self.send_dendrite_request(request)

    async def get_discord_profile(self, user_id: str):

        return []

    async def get_discord_channel_messages(self, channel_id: str):

        return []

    async def get_discord_guild_channels(self, guild_id: str):

        return []

    async def get_discord_user_guilds(self):

        return []

    async def get_discord_all_guilds(
        self,
    ):

        return []

    def get_axons(self):
        return self.validator.metagraph.axons

    def healthcheck(self):
        return {
            "coldkey": self.validator.wallet.coldkeypub.ss58_address,
            "hotkey": self.validator.wallet.hotkey.ss58_address,
            "is_active": True,
            "name": self.validator.config.neuron.name,
        }

    def start_server(self):
        config = uvicorn.Config(app=self.app, host=self.host, port=self.port)
        server = uvicorn.Server(config)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(server.serve())
        except KeyboardInterrupt:
            # Handle the keyboard interrupt to shutdown the server
            loop.run_until_complete(server.shutdown())
        finally:
            # Close the loop to clean up properly
            loop.close()
            asyncio.set_event_loop(None)  # Reset the event loop

    async def get_self(self):
        return self
