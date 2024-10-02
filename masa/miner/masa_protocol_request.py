import os
import requests
import bittensor as bt

# Set to 90 to account for discord/guilds/all on oracle node taking around 1 minute
REQUEST_TIMEOUT_IN_SECONDS = 90


class MasaProtocolRequest:
    def __init__(self):
        self.base_url = os.getenv("ORACLE_BASE_URL", "http://localhost:8080/api/v1")
        self.headers = {"Authorization": ""}

    def get(self, path) -> requests.Response:
        return requests.get(
            f"{self.base_url}{path}",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_IN_SECONDS,
        )

    def post(self, path, body) -> requests.Response:
        return requests.post(
            f"{self.base_url}{path}",
            json=body,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_IN_SECONDS,
        )

    def format(self, response: requests.Response):
        try:
            data = dict(response.json()).get("data", [])
            if not data:
                bt.logging.error("No data found in protocol response")
                return []
            return data
        except (ValueError, KeyError) as e:
            bt.logging.error(f"Error formatting protocol response: {e}")
            return []
