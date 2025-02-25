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
        Currently disabled - always returns True.

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
        bt.logging.debug(
            f"Tweet validation disabled - automatically passing tweet {tweet_id}"
        )
        return True
