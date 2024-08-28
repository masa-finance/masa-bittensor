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
        if response.ok:
            data = self.format(response)
            return data
        else:
            bt.logging.error(
                f"Worker request failed with response: {response.status_code}"
            )
            return None
