import bittensor as bt
from typing import Dict, Any
import aiohttp
from datetime import datetime, UTC, timedelta


async def validate_tweet(self, tweet: Dict[str, Any]) -> bool:
    """Validate a single tweet."""
    try:
        # Check required fields
        if not tweet or not isinstance(tweet, dict):
            return False

        required_fields = ["id", "text", "username", "timestamp"]
        if not all(field in tweet for field in required_fields):
            bt.logging.debug(
                f"Missing required fields in tweet: {tweet.get('id', 'unknown')}"
            )
            return False

        # Validate timestamp
        tweet_timestamp = datetime.fromtimestamp(tweet.get("timestamp", 0), UTC)
        yesterday = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
        if tweet_timestamp < yesterday:
            bt.logging.debug(f"Tweet {tweet['id']} is too old")
            return False

        # Tweet passed all validation checks
        bt.logging.debug(f"🟢 Tweet {self.format_tweet_url(tweet['id'])} is valid")
        return True

    except Exception as e:
        bt.logging.error(f"🔴 Error validating tweet: {e}")
        return False


async def send_to_protocol(self, chunk_index: int, data: Any) -> bool:
    """Send data to the protocol API."""
    try:
        api_url = self.config.validator.export_url
        if not api_url:
            bt.logging.warning("Missing config --validator.export_url")
            return False

        async with aiohttp.ClientSession() as session:
            payload = {
                "Hotkey": self.wallet.hotkey.ss58_address,
                "ChunkIndex": chunk_index,
                "Data": data,
            }

            async with session.post(api_url, json=payload) as response:
                if response.status == 200:
                    bt.logging.info(
                        f"✅ Successfully sent chunk {chunk_index} to protocol API"
                    )
                    return True
                else:
                    bt.logging.error(
                        f"❌ Failed to send chunk {chunk_index}: {response.status}"
                    )
                    return False

    except Exception as e:
        bt.logging.error(f"🔴 Failed to send data to protocol API: {e}")
        return False
