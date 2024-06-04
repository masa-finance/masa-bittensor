import os
from fastapi import FastAPI
import uvicorn
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException, Depends

class ValidatorAPI:
    def __init__(self, validator, config=None):
        self.host = os.getenv('VALIDATOR_API_HOST', "0.0.0.0")
        self.port = os.getenv('VALIDATOR_API_PORT', 8000)
        
        self.validator = validator
        self.app = FastAPI()

        self.app.add_api_route(
            "/data/twitter/{profile}",
            self.get_twitter_profile,
            methods=["GET"],
            # dependencies=[Depends(self.get_self)],
            response_description="Get the Twitter profile for the given username"
        )
        
        self.app.add_api_route(
            "/axons",
            self.get_axons,
            methods=["POST"],
            dependencies=[Depends(self.get_self)],
        )
        
        self.start_server()
        
        
    async def get_twitter_profile(self, profile: str):
        responses = await self.validator.forward(profile)
        print(f"Responses: {responses}")
        return responses

    
    def get_axons(self, data: dict = {}):
        print(f"Data: {data}")
        return self.validator.metagraph.axons
        
    def start_server(self):
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.executor.submit(
            uvicorn.run, self.app, host=self.host, port=self.port
    )
 
    async def get_self(self):
        return self
    
    