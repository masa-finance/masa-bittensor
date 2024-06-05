import os
from fastapi import FastAPI
import asyncio
import uvicorn
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException, Depends
from masa.api.request import RequestType

class ValidatorAPI:
    def __init__(self, validator, config=None):
        self.host = os.getenv('VALIDATOR_API_HOST', "0.0.0.0")
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
            "/data/twitter/tweets/recent/{query}",
            self.get_recent_tweets,
            methods=["GET"],
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
        return await self.validator.forward(query=username, type=RequestType.TWITTER_PROFILE.value)
    

    async def get_twitter_followers(self, username: str):
        return await self.validator.forward(query=username, type=RequestType.TWITTER_FOLLOWERS.value)
    

    async def get_recent_tweets(self, query: str):
        return await self.validator.forward(query=query, type=RequestType.TWITTER_TWEETS.value)

    
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
    
    