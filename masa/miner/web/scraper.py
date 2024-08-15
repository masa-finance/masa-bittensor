from dataclasses import dataclass
import requests
import bittensor as bt
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
        bt.logging.info(f"Getting scraped data from worker with query: {query}")
        response = self.post("/data/web", body={"url": query.url, "depth": query.depth})

        if response.status_code == 504:
            bt.logging.error("Worker request failed")
            return None
        scraped_data = self.format_scraped_data(response)
        return scraped_data

    def format_scraped_data(self, data: requests.Response) -> WebScraperObject:
        bt.logging.info(f"Formatting scraped data: {data}")
        json_data = data.json()["data"]

        formatted_scraped_data = WebScraperObject(**json_data)

        return formatted_scraped_data
