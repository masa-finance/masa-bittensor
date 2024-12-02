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

        self.app.add_api_route(
            "/scores",
            self.show_scores,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Show scores",
            tags=["scoring"],
        )

        self.app.add_api_route(
            "/tweets_by_uid",
            self.show_tweets_by_uid,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get indexed tweets by UID",
            tags=["data"],
        )

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

    async def show_tweets_by_uid(self):
        tweets = self.validator.tweets_by_uid
        if len(tweets) > 0:
            serializable_tweets = {
                uid: list(tweet_set) for uid, tweet_set in tweets.items()
            }
            return JSONResponse(content=serializable_tweets)
        return JSONResponse(content=[])

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
