from dataclasses import dataclass
import json
import requests
import bittensor as bt
from typing import List
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.web import WebScraperObject

@dataclass
class WebScraperQuery:
    url: str
    depth: int

class WebScraperRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()


    def scrape_web(self, query: WebScraperQuery) -> WebScraperObject:
        bt.logging.info(f"Getting recent tweets from worker with query: {query}")
        response = self.post(f"/data/web", body={"url": query.url, "depth": query.depth})
        
        if response.status_code == 504:
            bt.logging.error("Worker request failed")
            return None
        scraped_data = self.format_scraped_data(response)
        return scraped_data
        
        
    def format_scraped_data(self, data: requests.Response) -> WebScraperObject:
        bt.logging.info(f"Formatting scraped data: {data}")
        scraped_data = json.loads(data.json()['data']) # Convert stringified json to dict
        formatted_scraped_data = WebScraperObject(**scraped_data)
        
        return formatted_scraped_data
            
