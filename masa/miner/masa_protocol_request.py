import os
import requests
import bittensor as bt

# Default connection timeout
CONNECTION_TIMEOUT = 30
# Higher read timeout to prevent "Read timed out" errors
READ_TIMEOUT = 60


class MasaProtocolRequest:
    def __init__(self):
        self.base_url = os.getenv("ORACLE_BASE_URL", "http://localhost:8080/api/v1")
        self.headers = {"Authorization": ""}

    def get(self, path, timeout=CONNECTION_TIMEOUT) -> requests.Response:
        # Always use a tuple with the specified connection timeout and our fixed read timeout
        return requests.get(
            f"{self.base_url}{path}",
            headers=self.headers,
            timeout=(timeout, READ_TIMEOUT),
        )

    def post(self, path, body, timeout=CONNECTION_TIMEOUT) -> requests.Response:
        # Always use a tuple with the specified connection timeout and our fixed read timeout
        return requests.post(
            f"{self.base_url}{path}",
            json=body,
            headers=self.headers,
            timeout=(timeout, READ_TIMEOUT),
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
