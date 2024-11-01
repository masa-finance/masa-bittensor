import os
import asyncio
import uvicorn

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


class API:
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
            "/data/twitter/profile",
            self.validator.forwarder.get_twitter_profile,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the Twitter profile for the given username",
            tags=["twitter"],
        )

        self.app.add_api_route(
            "/data/twitter/followers",
            self.validator.forwarder.get_twitter_followers,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the Twitter followers for the given username",
            tags=["twitter"],
        )

        self.app.add_api_route(
            "/data/twitter/tweets/recent",
            self.validator.forwarder.get_recent_tweets,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get recent tweets given a query",
            tags=["twitter"],
        )

        # self.app.add_api_route(
        #     "/data/discord/profile",
        #     self.validator.forwarder.get_discord_profile,
        #     methods=["GET"],
        #     dependencies=[Depends(self.get_self)],
        #     response_description="Get the Discord profile for the given user ID",
        #     tags=["discord"],
        # )

        # self.app.add_api_route(
        #     "/data/discord/channels/{channel_id}/messages",
        #     self.validator.forwarder.get_discord_channel_messages,
        #     methods=["GET"],
        #     dependencies=[Depends(self.get_self)],
        #     response_description="Get the Discord channel messages for the given channel ID",
        #     tags=["discord"],
        # )

        # self.app.add_api_route(
        #     "/data/discord/guilds/{guild_id}/channels",
        #     self.validator.forwarder.get_discord_guild_channels,
        #     methods=["GET"],
        #     dependencies=[Depends(self.get_self)],
        #     response_description="Get the Discord channels for the given guild ID",
        #     tags=["discord"],
        # )

        # self.app.add_api_route(
        #     "/data/discord/user/guilds",
        #     self.validator.forwarder.get_discord_user_guilds,
        #     methods=["GET"],
        #     dependencies=[Depends(self.get_self)],
        #     response_description="Get the Discord guilds for the user",
        #     tags=["discord"],
        # )

        # self.app.add_api_route(
        #     "/data/discord/guilds/all",
        #     self.validator.forwarder.get_discord_all_guilds,
        #     methods=["GET"],
        #     dependencies=[Depends(self.get_self)],
        #     response_description="Get all guilds that all the Discord workers are apart of",
        #     tags=["discord"],
        # )

        # note, healthcheck for the validator
        self.app.add_api_route(
            "/healthcheck",
            self.healthcheck,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get healthcheck status",
            tags=["metagraph"],
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
            "/ping",
            self.validator.forwarder.ping_axons,
            methods=["POST"],
            dependencies=[Depends(self.get_self)],
            response_description="Ping Axons",
            tags=["metagraph"],
        )

        self.app.add_api_route(
            "/volumes",
            self.show_miner_volumes,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get scores and capacity of miners",
            tags=["scoring"],
        )

        # note, only for testing / wiping state
        # self.app.add_api_route(
        #     "/volumes",
        #     self.delete_miner_volumes,
        #     methods=["DELETE"],
        #     dependencies=[Depends(self.get_self)],
        #     response_description="Delete volumes state",
        #     tags=["scoring"],
        # )

        # note, only for testing, this also runs on a dedciated thread
        # self.app.add_api_route(
        #     "/score",
        #     self.validator.scorer.score_miner_volumes,
        #     methods=["GET"],
        #     dependencies=[Depends(self.get_self)],
        #     response_description="Score miner volumes",
        #     tags=["scoring"],
        # )

        # note, show the scores the validator has computed
        self.app.add_api_route(
            "/scores",
            self.show_scores,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Show scores",
            tags=["scoring"],
        )

        self.app.add_api_route(
            "/tweets_by_query",
            self.show_tweets_by_query,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get indexed tweets by query",
            tags=["data"],
        )

        self.app.add_api_route(
            "/tweets_by_uid",
            self.show_tweets_by_uid,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get indexed tweets by UID",
            tags=["data"],
        )

        # note, only for testing / wiping state
        # self.app.add_api_route(
        #     "/tweets",
        #     self.delete_tweets_by_query,
        #     methods=["DELETE"],
        #     dependencies=[Depends(self.get_self)],
        #     response_description="Delete indexed tweets",
        #     tags=["data"],
        # )

        self.start_server()

    async def show_miner_volumes(self):
        volumes = self.validator.volumes
        if volumes:
            serializable_volumes = [
                {
                    "tempo": int(volume["tempo"]),
                    "miners": {int(k): float(v) for k, v in volume["miners"].items()},
                }
                for volume in volumes
            ]
            return JSONResponse(content=serializable_volumes)
        return JSONResponse(content=[])

    async def show_scores(self):
        scores = self.validator.scores
        if len(scores) > 0:
            return JSONResponse(content=scores.tolist())
        return JSONResponse(content=[])

    async def show_tweets_by_query(self):
        tweets = self.validator.tweets_by_query
        if len(tweets) > 0:
            return JSONResponse(content=tweets)
        return JSONResponse(content=[])

    async def show_tweets_by_query(self):
        tweets = self.validator.tweets_by_uid
        if len(tweets) > 0:
            return JSONResponse(content=tweets)
        return JSONResponse(content=[])

    def delete_miner_volumes(self):
        self.validator.volumes = []
        return JSONResponse(
            content={
                "message": "Volumes state deleted",
                "volumes": self.validator.volumes,
            }
        )

    def delete_tweets_by_query(self):
        self.validator.tweets_by_query = []
        return JSONResponse(
            content={
                "message": "Index tweets deleted",
                "volumes": self.validator.tweets_by_query,
            }
        )

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
