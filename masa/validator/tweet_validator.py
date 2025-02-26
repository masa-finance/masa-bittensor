import os
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime
import bittensor as bt
import json

DEFAULT_BASE_URL = "https://test.protocol-api.masa.ai"
DEFAULT_TWEET_API_PATH = "/api/v1/data/twitter/tweets"


class TweetValidator:
    def __init__(self):
        self.base_url = os.getenv("MASA_BASE_URL", DEFAULT_BASE_URL)
        self.api_path = os.getenv("MASA_API_PATH", DEFAULT_TWEET_API_PATH)
        self.api_key = os.getenv("API_KEY")

    async def validate_tweet(
        self,
        tweet_id: str,
        name: str,
        username: str,
        text: str,
        timestamp: int,
        hashtags: list,
    ) -> bool:
        """
        Validate a tweet by checking it against the Masa protocol API.

        Args:
            tweet_id (str): The ID of the tweet to validate
            name (str): The name of the tweet author
            username (str): The username of the tweet author
            text (str): The text content of the tweet
            timestamp (int): The timestamp of the tweet
            hashtags (list): List of hashtags in the tweet

        Returns:
            bool: True if the tweet is valid, False otherwise
        """
        if not self.api_key:
            bt.logging.error("No API key configured for tweet validation")
            return False

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "id": tweet_id,
                "name": name,
                "username": username,
                "text": text,
                "timestamp": timestamp,
                "hashtags": hashtags,
            }

            bt.logging.debug(
                f"Sending validation request for tweet {tweet_id} to {self.base_url}{self.api_path}"
            )
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}{self.api_path}", headers=headers, json=payload
                ) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        result = json.loads(response_text)
                        is_valid = result.get("exists", False)
                        bt.logging.debug(
                            f"Tweet {tweet_id} validation result: {is_valid}"
                        )
                        return is_valid
                    else:
                        bt.logging.error(
                            f"Tweet validation API returned status {response.status}\n"
                            f"URL: {self.base_url}{self.api_path}\n"
                            f"Request payload: {json.dumps(payload, indent=2)}\n"
                            f"Response body: {response_text}"
                        )
                        return False

        except Exception as e:
            bt.logging.error(f"Error validating tweet {tweet_id}: {str(e)}")
            return False
