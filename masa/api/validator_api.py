import os
from fastapi import FastAPI
import asyncio
import uvicorn
from fastapi import FastAPI, Depends
from masa.miner.twitter.tweets import RecentTweetsQuery
from masa.validator.twitter.profile.forward import ProfileForwarder
from masa.validator.twitter.followers.forward import FollowersForwarder
from masa.validator.twitter.tweets.forward import TweetsForwarder

class ValidatorAPI:
    def __init__(self, validator, config=None):
        self.host = os.getenv('VALIDATOR_API_HOST', "localhost")
        self.port = int(os.getenv('VALIDATOR_API_PORT', "8000"))
        
        self.validator = validator
        self.app = FastAPI()

        self.app.add_api_route(
            "/data/twitter/profile/{username}",
            self.get_twitter_profile,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the Twitter profile for the given username",
            tags=["twitter"]
        )

        self.app.add_api_route(
            "/data/twitter/followers/{username}",
            self.get_twitter_followers,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the Twitter followers for the given username",
            tags=["twitter"]
        )

        self.app.add_api_route(
            "/data/twitter/tweets/recent",
            self.get_recent_tweets,
            methods=["POST"],
            dependencies=[Depends(self.get_self)],
            response_description="Get recent tweets given a query",
            tags=["twitter"]
        )
        
        self.app.add_api_route(
            "/axons",
            self.get_axons,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
            response_description="Get the axons for the given metagraph",
            tags=["metagraph"]
        )
        
        self.start_server()
        
        
    async def get_twitter_profile(self, username: str):
        return await ProfileForwarder(self.validator).forward_query(query=username)

    async def get_twitter_followers(self, username: str):
        return await FollowersForwarder(self.validator).forward_query(query=username)
    
    async def get_recent_tweets(self, tweet_query: RecentTweetsQuery):
        return await TweetsForwarder(self.validator).forward_query(tweet_query=tweet_query)

    def get_axons(self):
        return self.validator.metagraph.axons
        
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
    
    