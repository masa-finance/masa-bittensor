import os
from fastapi import FastAPI, Depends
import asyncio
import uvicorn
from masa.miner.twitter.tweets import RecentTweetsQuery
from masa.miner.web.scraper import WebScraperQuery
from masa.validator.twitter.profile.forward import TwitterProfileForwarder
from masa.validator.twitter.followers.forward import TwitterFollowersForwarder
from masa.validator.twitter.tweets.forward import TwitterTweetsForwarder
from masa.validator.web.forward import WebScraperForwarder
from masa.validator.discord.channel_messages.forward import (
    DiscordChannelMessagesForwarder,
)
from masa.validator.discord.guild_channels.forward import DiscordGuildChannelsForwarder
from masa.validator.discord.user_guilds.forward import DiscordUserGuildsForwarder
from masa.validator.discord.profile.forward import DiscordProfileForwarder
from masa.validator.discord.all_guilds.forward import DiscordAllGuildsForwarder
from fastapi.middleware.cors import CORSMiddleware


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
            "/data/twitter/profile/{username}",
            self.get_twitter_profile,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the Twitter profile for the given username",
            tags=["twitter"],
        )

        self.app.add_api_route(
            "/data/twitter/followers/{username}",
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
            "/data/web",
            self.scrape_web,
            methods=["POST"],
            dependencies=[Depends(self.get_self)],
            response_description="Scrape a website given a url",
            tags=["web"],
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

        self.start_server()

    async def get_twitter_profile(self, username: str):
        all_responses = await TwitterProfileForwarder(self.validator).forward_query(
            query=username
        )
        if all_responses:
            return all_responses
        return []

    async def get_twitter_followers(self, username: str):
        all_responses = await TwitterFollowersForwarder(self.validator).forward_query(
            query=username
        )
        if all_responses:
            return all_responses
        return []

    async def get_recent_tweets(self, tweet_query: RecentTweetsQuery):
        all_responses = await TwitterTweetsForwarder(self.validator).forward_query(
            tweet_query=tweet_query
        )
        if all_responses:
            return all_responses
        return []

    async def scrape_web(self, web_scraper_query: WebScraperQuery):
        all_responses = await WebScraperForwarder(self.validator).forward_query(
            web_scraper_query=web_scraper_query
        )
        if all_responses:
            return all_responses
        return []

    async def get_discord_profile(self, user_id: str):
        all_responses = await DiscordProfileForwarder(self.validator).forward_query(
            query=user_id
        )
        if all_responses:
            return all_responses
        return []

    async def get_discord_channel_messages(self, channel_id: str):
        all_responses = await DiscordChannelMessagesForwarder(
            self.validator
        ).forward_query(query=channel_id)
        if all_responses:
            return all_responses
        return []

    async def get_discord_guild_channels(self, guild_id: str):
        all_responses = await DiscordGuildChannelsForwarder(
            self.validator
        ).forward_query(query=guild_id)
        if all_responses:
            return all_responses
        return []

    async def get_discord_user_guilds(self):
        all_responses = await DiscordUserGuildsForwarder(self.validator).forward_query()
        if all_responses:
            return all_responses
        return []

    async def get_discord_all_guilds(self):
        all_responses = await DiscordAllGuildsForwarder(self.validator).forward_query()
        if all_responses:
            return all_responses
        return []

    def get_axons(self):
        return self.validator.metagraph.axons
    
    def healthcheck(self):
        return {
            "coldkey": self.validator.wallet.coldkeypub.ss58_address,
            "hotkey": self.validator.wallet.hotkey.ss58_address,
            "is_active": True,
            "name": self.validator.config.neuron.name
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
