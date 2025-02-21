import os
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime
import bittensor as bt

DEFAULT_BASE_URL = "https://test.protocol-api.masa.ai"
DEFAULT_TWEET_API_PATH = "/api/v1/data/twitter/tweets"


class TweetValidator:
    def __init__(self):
        self.base_url = os.getenv("MASA_BASE_URL", DEFAULT_BASE_URL)
        self.api_path = os.getenv("MASA_API_PATH", DEFAULT_TWEET_API_PATH)

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
        try:
            # Construct API URL
            api_url = (
                f"{self.base_url.rstrip('/')}/{self.api_path.lstrip('/')}/{tweet_id}"
            )

            # Headers for the request
            headers = {"accept": "application/json", "Content-Type": "application/json"}

            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers) as response:
                    if response.status == 404:
                        bt.logging.debug(f"Tweet {tweet_id} not found")
                        return False

                    response.raise_for_status()
                    response_data = await response.json()

                    if (
                        not response_data
                        or "data" not in response_data
                        or not response_data["data"]
                    ):
                        bt.logging.debug(f"No data returned for tweet {tweet_id}")
                        return False

                    # Extract tweet data from response
                    tweet_data = response_data["data"]

                    # Validate tweet fields
                    if (
                        tweet_data.get("name") != name
                        or tweet_data.get("username") != username
                        or tweet_data.get("text") != text
                        or abs(tweet_data.get("timestamp", 0) - timestamp)
                        > 1  # Allow 1 second difference
                        or set(tweet_data.get("hashtags", [])) != set(hashtags)
                    ):
                        bt.logging.debug(f"Tweet {tweet_id} data mismatch")
                        return False

                    return True

        except aiohttp.ClientError as e:
            bt.logging.error(f"API request error for tweet {tweet_id}: {str(e)}")
            return False
        except Exception as e:
            bt.logging.error(f"Validation error for tweet {tweet_id}: {str(e)}")
            return False
