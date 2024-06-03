from fastapi import FastAPI
import uvicorn
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException, Depends

class ValidatorAPI:
    def __init__(self, validator, config=None):
        # super(ValidatorAPI, self).__init__(config=config)
        self.validator = validator
        self.app = FastAPI()
        self.app.add_api_route(
            "/twitter-profile",
            self.get_twitter_profile,
            methods=["GET"],
            dependencies=[Depends(self.get_self)],
        )
        
        self.app.add_api_route(
            "/axons",
            self.get_axons,
            methods=["POST"],
            dependencies=[Depends(self.get_self)],
        )
        
        self.start_server()
        
        
        
    async def get_twitter_profile(self, data: dict = {}):
        print(f"Data: {data}")
        return await self.validator.forward("brendanplayford")

    
    def get_axons(self, data: dict = {}):
        print(f"Data: {data}")
        return self.validator.metagraph.axons
        
    def start_server(self):
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.executor.submit(
            uvicorn.run, self.app, host="0.0.0.0", port=8000
    )
 
    async def get_self(self):
        return self
    
    