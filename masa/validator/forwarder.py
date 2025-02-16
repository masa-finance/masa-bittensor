# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Masa

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import bittensor as bt
from typing import Any, List, Tuple
from datetime import datetime, UTC, timedelta
import aiohttp
import json
import random
import asyncio
from masa.synapses import (
    RecentTweetsSynapse,
    TwitterFollowersSynapse,
    TwitterProfileSynapse,
)

from masa.synapses import PingAxonSynapse
from masa.base.healthcheck import get_external_ip
from masa.utils.uids import get_random_miner_uids, get_uncalled_miner_uids

from masa_ai.tools.validator import TrendingQueries, TweetValidator

import re
import sys
import os


# Add this class to silence masa-ai output
class SilentOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.devnull, "w")

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout
        sys.stderr.close()
        sys.stderr = self._original_stderr


class Forwarder:
    def __init__(self, validator):
        self.validator = validator
        # Add state for pending validations
        if not hasattr(self.validator, "pending_validations"):
            self.validator.pending_validations = (
                {}
            )  # uid -> {tweet_id -> {tweet_data, attempts, last_attempt}}

    async def forward_request(
        self,
        request: Any,
        sample_size: int = None,
        timeout: int = None,
        sequential: bool = False,
    ):
        if not sample_size:
            sample_size = self.validator.subnet_config.get("organic").get("sample_size")
        if not timeout:
            timeout = self.validator.subnet_config.get("organic").get("timeout")
        if sequential:
            miner_uids = await get_uncalled_miner_uids(self.validator, k=sample_size)
        else:
            miner_uids = await get_random_miner_uids(self.validator, k=sample_size)

        if miner_uids is None or len(miner_uids) == 0:
            return [], []

        try:
            async with bt.dendrite(wallet=self.validator.wallet) as dendrite:
                responses = await dendrite(
                    [self.validator.metagraph.axons[uid] for uid in miner_uids],
                    request,
                    deserialize=True,
                    timeout=timeout,
                )

                # Handle potential None responses
                formatted_responses = []
                for uid, response in zip(miner_uids, responses):
                    hotkey = self.validator.metagraph.hotkeys[uid]
                    taostats_link = f"https://taostats.io/hotkey/{hotkey}"

                    if response is None:
                        bt.logging.info(
                            f"Miner: {uid}, Status: No response, Link: {taostats_link}"
                        )
                        formatted_responses.append({"uid": int(uid), "response": None})
                    else:
                        # Extract response metrics
                        resp_data = (
                            response.get("response", [])
                            if isinstance(response, dict)
                            else []
                        )
                        tweet_count = (
                            len(resp_data) if isinstance(resp_data, list) else 0
                        )

                        # Only log at debug level since this will be summarized later
                        bt.logging.debug(
                            f"Miner: {uid}, Status: Response received, Link: {taostats_link}"
                        )
                        formatted_responses.append(
                            {"uid": int(uid), "response": response}
                        )

                return formatted_responses, miner_uids

        except Exception as e:
            bt.logging.error(f"Error in forward_request: {e}")
            # Return empty responses but with proper structure for error handling
            return [
                {"uid": int(uid), "response": None} for uid in miner_uids
            ], miner_uids

    async def get_twitter_profile(self, username: str = "getmasafi"):
        request = TwitterProfileSynapse(username=username)
        formatted_responses, _ = await self.forward_request(
            request=request,
        )
        return formatted_responses

    async def get_twitter_followers(self, username: str = "getmasafi", count: int = 10):
        request = TwitterFollowersSynapse(username=username, count=count)
        formatted_responses, _ = await self.forward_request(
            request=request,
        )
        return formatted_responses

    async def get_recent_tweets(
        self,
        query: str = f"(Bitcoin) since:{datetime.now().strftime('%Y-%m-%d')}",
        count: int = 3,
    ):
        request = RecentTweetsSynapse(
            query=query,
            count=count,
            timeout=self.validator.subnet_config.get("organic").get("timeout"),
        )
        formatted_responses, _ = await self.forward_request(
            request=request,
        )
        return formatted_responses

    async def get_discord_profile(self, user_id: str = "449222160687300608"):
        return ["Not yet implemented"]

    async def get_discord_channel_messages(self, channel_id: str):
        return ["Not yet implemented"]

    async def get_discord_guild_channels(self, guild_id: str):
        return ["Not yet implemented"]

    async def get_discord_user_guilds(self):
        return ["Not yet implemented"]

    async def get_discord_all_guilds(self):
        return ["Not yet implemented"]

    def _summarize_versions(self, versions):
        """Summarize version distribution and count unreachable miners."""
        version_counts = {}
        unreachable = 0
        for v in versions:
            if v == 0:
                unreachable += 1
            else:
                version_counts[v] = version_counts.get(v, 0) + 1

        # Format the summary string
        total_miners = len(versions)
        reachable = total_miners - unreachable
        summary_parts = [f"🔍 Miners: {reachable}/{total_miners} online"]

        if version_counts:
            version_str = ", ".join(
                f"v{v}:{count}" for v, count in sorted(version_counts.items())
            )
            summary_parts.append(f"Versions: {version_str}")

        if unreachable > 0:
            summary_parts.append(f"Unreachable: {unreachable}")

        return " | ".join(summary_parts)

    async def ping_axons(self, current_block: int):
        request = PingAxonSynapse(
            sent_from=get_external_ip(),
            is_active=False,
            version=int("0"),  # Ensure version is an integer
        )
        sample_size = self.validator.subnet_config.get("healthcheck").get("sample_size")
        all_responses = []

        # Filter out validators (they have nonzero validator_trust)
        miner_axons = []
        miner_indices = []
        for idx, axon in enumerate(self.validator.metagraph.axons):
            if (
                self.validator.metagraph.validator_trust[idx] == 0
            ):  # Only include miners
                miner_axons.append(axon)
                miner_indices.append(idx)

        total_miners = len(miner_axons)
        successful_pings = 0
        failed_pings = 0

        bt.logging.info(
            f"Starting to ping {total_miners} miners in batches of {sample_size}"
        )

        async with bt.dendrite(wallet=self.validator.wallet) as dendrite:
            for i in range(0, total_miners, sample_size):
                batch = miner_axons[i : i + sample_size]
                batch_responses = await dendrite(
                    batch,
                    request,
                    deserialize=False,
                    timeout=self.validator.subnet_config.get("healthcheck").get(
                        "timeout"
                    ),
                )
                all_responses.extend(batch_responses)

                # Count successes and failures for this batch
                batch_success = sum(1 for r in batch_responses if r.version > 0)
                batch_failed = len(batch_responses) - batch_success
                successful_pings += batch_success
                failed_pings += batch_failed

                # Progress update every batch
                progress = min(100, (i + len(batch)) * 100 // total_miners)
                bt.logging.info(
                    f"Ping progress: {progress}% | "
                    f"Success: {successful_pings} | "
                    f"Failed: {failed_pings}"
                )

        # Initialize versions array with zeros for all nodes
        self.validator.versions = [0] * len(self.validator.metagraph.axons)

        # Update versions only for miners we pinged
        for idx, response in zip(miner_indices, all_responses):
            self.validator.versions[idx] = response.version

        # Use the summarize function for a cleaner log
        version_summary = self._summarize_versions(
            [
                v
                for i, v in enumerate(self.validator.versions)
                if self.validator.metagraph.validator_trust[i] == 0
            ]
        )
        bt.logging.info(f"🔍 Miner Status: {version_summary}")

        # Keep detailed version list at DEBUG level
        bt.logging.debug(f"Detailed Miner Versions: {self.validator.versions}")

        self.validator.last_healthcheck_block = current_block
        return [
            {
                "status_code": response.dendrite.status_code,
                "status_message": response.dendrite.status_message,
                "version": response.version,
                "uid": miner_indices[all_responses.index(response)],
            }
            for response in all_responses
        ]

    async def fetch_twitter_queries(self):
        try:
            trending_queries = TrendingQueries().fetch()
            self.validator.keywords = [
                query["query"] for query in trending_queries[:10]  # top 10 trends
            ]
            bt.logging.info(f"Trending queries: {self.validator.keywords}")
        except Exception as e:
            # handle failed fetch - default to popular keywords
            bt.logging.error(f"Error fetching trending queries: {e}")
            self.validator.keywords = ["crypto", "btc", "eth"]

    async def get_miners_volumes(self, current_block: int):
        """Get and validate tweet volumes from miners."""
        # Initialize validation
        if len(self.validator.versions) == 0:
            bt.logging.info("🔍 Pinging axons to get miner versions...")
            return await self.ping_axons(current_block)

        if len(self.validator.keywords) == 0 or self.check_tempo(current_block):
            await self.fetch_twitter_queries()

        # Select query and create request
        random_keyword = random.choice(self.validator.keywords)
        query = f'"{random_keyword.strip()}"'
        bt.logging.info(f"🔍 Volume checking for: {query}")

        # Get miner responses
        responses, miner_uids = await self._get_miner_responses(query)
        if not responses:
            return

        bt.logging.info("Selected miners to query")
        bt.logging.info(f"Selected UIDs: {miner_uids}")

        # Process responses
        all_valid_tweets = await self._process_responses(
            responses, miner_uids, random_keyword, current_block
        )

        # Export valid tweets
        if all_valid_tweets:
            await self.validator.export_tweets(
                list(
                    {tweet["Tweet"]["ID"]: tweet for tweet in all_valid_tweets}.values()
                ),
                query.strip().replace('"', ""),
            )

        self.validator.last_volume_block = current_block

    async def _get_miner_responses(self, query: str):
        """Get responses from selected miners."""
        request = RecentTweetsSynapse(
            query=query,
            timeout=self.validator.subnet_config.get("synthetic").get("timeout"),
        )

        return await self.forward_request(
            request,
            sample_size=self.validator.subnet_config.get("synthetic").get(
                "sample_size"
            ),
            timeout=self.validator.subnet_config.get("synthetic").get("timeout"),
            sequential=True,
        )

    def _validate_tweet_structure(self, tweet):
        """Check if tweet has valid structure and ID."""
        return (
            isinstance(tweet, dict)
            and "Tweet" in tweet
            and "ID" in tweet["Tweet"]
            and tweet["Tweet"]["ID"]
            and str(tweet["Tweet"]["ID"]).strip().isdigit()
        )

    def _check_tweet_content(self, tweet_data, query_words):
        """Check if tweet content matches query terms."""
        if not tweet_data or not query_words:
            return False

        # Log the tweet data we're checking
        bt.logging.debug(
            f"Checking tweet content: {tweet_data.get('Text', '')[:100]}..."
        )
        bt.logging.debug(f"Against query words: {query_words}")

        # Get all the fields we want to check
        text = self.normalize_whitespace(tweet_data.get("Text", "")).lower()
        name = self.normalize_whitespace(tweet_data.get("Name", "")).lower()
        username = self.normalize_whitespace(tweet_data.get("Username", "")).lower()
        hashtags = [tag.lower() for tag in tweet_data.get("Hashtags", [])]

        # Combine all fields into one string for easier searching
        searchable_content = f"{text} {name} {username} {' '.join(hashtags)}".lower()

        # First try exact phrase match if multiple words
        if len(query_words) > 1:
            exact_phrase = " ".join(query_words).lower()
            if exact_phrase in searchable_content:
                bt.logging.debug(f"Found exact phrase match: {exact_phrase}")
                return True

        # For single words or if phrase match fails, check each word
        for word in query_words:
            word = word.lower()
            if word in searchable_content:
                bt.logging.debug(f"Found word match: {word}")
                return True

        return False

    def _check_tweet_timestamp(self, timestamp):
        """Check if tweet meets recency requirements."""
        tweet_time = datetime.fromtimestamp(timestamp, UTC)
        yesterday = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
        return yesterday <= tweet_time

    def _process_single_response(self, resp, uid):
        """Process a single miner's response and return valid tweets."""
        # First handle non-list responses
        if not isinstance(resp, list):
            bt.logging.debug(f"└─ Miner {uid}: Invalid response type: {type(resp)}")
            return [], 0, 0

        if not resp:
            bt.logging.debug(f"└─ Miner {uid}: Empty response list")
            return [], 0, 0

        # Count error items first
        error_items = []
        valid_items = []

        for item in resp:
            # Skip if item is not a dict
            if not isinstance(item, dict):
                continue

            # Check for error items
            if item.get("Error"):
                error_items.append(item)
                continue

            # Get tweet data, handling different possible formats
            tweet_data = None
            if "Tweet" in item:
                tweet_data = item.get("Tweet")
            elif "tweet" in item:
                tweet_data = item.get("tweet")
            else:
                # If the item itself has tweet-like fields, treat it as tweet data
                required_fields = ["ID", "Text", "Timestamp"]
                if all(field in item for field in required_fields):
                    tweet_data = item

            # Skip if no valid tweet data found
            if not isinstance(tweet_data, dict):
                continue

            # Normalize tweet ID format
            tweet_id = tweet_data.get("ID") or tweet_data.get("id")
            if not tweet_id or not str(tweet_id).strip().isdigit():
                continue

            # If we got here, we have a valid tweet structure
            valid_items.append({"Tweet": tweet_data})

        # Log results at debug level
        if error_items:
            bt.logging.debug(
                f"└─ Miner {uid}: Found {len(error_items)} items with errors"
            )
            if error_items:
                bt.logging.debug(
                    f"└─ Miner {uid}: Sample error: {error_items[0]['Error']}"
                )

        if valid_items:
            bt.logging.debug(f"└─ Miner {uid}: Found {len(valid_items)} valid tweets")

        return valid_items, len(error_items), len(valid_items)

    async def _process_responses(
        self, responses, miner_uids, random_keyword, current_block: int
    ):
        """Process responses from miners based on actual response structure."""
        all_valid_tweets = []
        validator = None

        # Initialize validator outside the loop to avoid recreation
        with SilentOutput():
            validator = TweetValidator()

        for response, uid in zip(responses, miner_uids):
            try:
                # Convert uid to int here, before any conditional logic
                uid_int = int(uid)

                # Handle None response
                if response is None or not isinstance(response, dict):
                    bt.logging.info(f"Miner {uid}: Invalid response format")
                    self.validator.scorer.add_volume(uid_int, 0, current_block)
                    continue

                all_responses = response.get("response", [])
                if not all_responses or not isinstance(all_responses, list):
                    bt.logging.info(f"Miner {uid}: No valid responses")
                    self.validator.scorer.add_volume(uid_int, 0, current_block)
                    continue

                bt.logging.info(
                    f"\n=== Processing {len(all_responses)} tweets from miner {uid} ==="
                )

                # First filter out tweets with invalid structure
                structured_tweets = []
                invalid_structure_count = 0
                for tweet in all_responses:
                    if not isinstance(tweet, dict):
                        invalid_structure_count += 1
                        continue

                    if (
                        "Tweet" in tweet
                        and isinstance(tweet["Tweet"], dict)
                        and "ID" in tweet["Tweet"]
                        and tweet["Tweet"]["ID"]
                    ):
                        tweet_id = str(tweet["Tweet"]["ID"]).strip()
                        if tweet_id.isdigit():
                            structured_tweets.append(tweet)
                        else:
                            invalid_structure_count += 1
                    else:
                        invalid_structure_count += 1

                if invalid_structure_count > 0:
                    bt.logging.info(
                        f"Miner {uid}: Found {invalid_structure_count} tweets with invalid structure"
                    )

                # Deduplicate tweets by ID
                unique_tweets = list(
                    {
                        tweet["Tweet"]["ID"]: tweet for tweet in structured_tweets
                    }.values()
                )
                bt.logging.info(
                    f"Miner {uid}: Found {len(unique_tweets)} tweets with valid structure"
                )

                if not unique_tweets:
                    bt.logging.info(f"Miner {uid}: No tweets with valid structure")
                    self.validator.scorer.add_volume(uid_int, 0, current_block)
                    continue

                # Select a random sample of tweets to validate (max 5)
                sample_size = min(5, len(unique_tweets))
                tweets_to_validate = random.sample(unique_tweets, sample_size)
                bt.logging.info(f"Miner {uid}: Validating {sample_size} random tweets")

                # Track validation results
                validation_failures = []
                query_failures = []
                timestamp_failures = []
                valid_tweets = []

                for tweet in tweets_to_validate:
                    tweet_data = tweet["Tweet"]
                    tweet_id = tweet_data["ID"]
                    tweet_url = self.format_tweet_url(tweet_id)

                    # Check timestamp first (cheapest check)
                    tweet_timestamp = datetime.fromtimestamp(
                        tweet_data.get("Timestamp", 0), UTC
                    )
                    yesterday = datetime.now(UTC).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ) - timedelta(days=1)
                    if not yesterday <= tweet_timestamp:
                        timestamp_failures.append((tweet_id, tweet_timestamp))
                        bt.logging.info(f"Tweet timestamp check failed: {tweet_url}")
                        bt.logging.debug(
                            f"Tweet time: {tweet_timestamp}, Required after: {yesterday}"
                        )
                        continue

                    # Check query match next (also cheap)
                    query_words = (
                        self.normalize_whitespace(random_keyword.replace('"', ""))
                        .strip()
                        .lower()
                        .split()
                    )
                    text = (
                        self.normalize_whitespace(tweet_data.get("Text", ""))
                        .strip()
                        .lower()
                    )

                    bt.logging.debug(f"Checking tweet {tweet_url}")
                    bt.logging.info(f"Query terms: {query_words}")
                    bt.logging.info(f"Tweet text: {tweet_data.get('Text', '')}")

                    # Check if any query word is in the text
                    if not self._check_tweet_content(tweet_data, query_words):
                        query_failures.append((tweet_id, text))
                        bt.logging.info(f"Query match failed for {tweet_url}")
                        bt.logging.info(f"  Query terms: {query_words}")
                        bt.logging.info(f"  Tweet text: {tweet_data.get('Text', '')}")
                        continue

                    # Finally do masa-ai validation (most expensive)
                    retry_count = 0
                    max_retries = 3
                    validation_success = False

                    while retry_count < max_retries and not validation_success:
                        try:
                            with SilentOutput():
                                is_valid = validator.validate_tweet(
                                    tweet_data.get("ID"),
                                    tweet_data.get("Name"),
                                    tweet_data.get("Username"),
                                    tweet_data.get("Text"),
                                    tweet_data.get("Timestamp"),
                                    tweet_data.get("Hashtags", []),
                                )

                            if is_valid:
                                valid_tweets.append(tweet)
                                validation_success = True
                                bt.logging.info(f"Tweet validation passed: {tweet_url}")
                                bt.logging.info(f"  Text: {tweet_data.get('Text', '')}")
                            else:
                                validation_failures.append(
                                    (tweet_id, "Tweet not found or invalid")
                                )
                                bt.logging.info(f"Tweet validation failed: {tweet_url}")
                                bt.logging.info(f"  Text: {tweet_data.get('Text', '')}")
                                break

                        except Exception as e:
                            if "429" in str(e) and retry_count < max_retries - 1:
                                wait_time = (2**retry_count) * 5
                                bt.logging.warning(
                                    f"Rate limited validating {tweet_url}, waiting {wait_time}s"
                                )
                                await asyncio.sleep(wait_time)
                                retry_count += 1
                            else:
                                validation_failures.append(
                                    (tweet_id, f"Error: {str(e)}")
                                )
                                bt.logging.error(
                                    f"Error validating {tweet_url}: {str(e)}"
                                )
                                break

                    # Always wait between validations
                    await asyncio.sleep(2)

                # Calculate validation success rate
                validation_success_rate = (
                    len(valid_tweets) / sample_size if sample_size > 0 else 0
                )
                bt.logging.info(
                    f"Miner {uid}: Validation success rate: {validation_success_rate:.2%}"
                )

                # Only credit miner if validation success rate is high enough (e.g. 80%)
                if validation_success_rate >= 0.8:
                    bt.logging.info(
                        f"Miner {uid}: Validation success rate sufficient, crediting tweets"
                    )
                    if not self.validator.tweets_by_uid.get(uid_int):
                        self.validator.tweets_by_uid[uid_int] = {
                            tweet["Tweet"]["ID"] for tweet in unique_tweets
                        }
                        self.validator.scorer.add_volume(
                            uid_int, len(unique_tweets), current_block
                        )
                        bt.logging.info(
                            f"Miner {uid_int} produced {len(unique_tweets)} new tweets"
                        )
                    else:
                        existing_tweet_ids = self.validator.tweets_by_uid[uid_int]
                        new_tweet_ids = {
                            tweet["Tweet"]["ID"] for tweet in unique_tweets
                        }
                        updates = new_tweet_ids - existing_tweet_ids
                        if updates:
                            self.validator.tweets_by_uid[uid_int].update(new_tweet_ids)
                            self.validator.scorer.add_volume(
                                uid_int, len(updates), current_block
                            )
                            bt.logging.info(
                                f"Miner {uid_int} produced {len(updates)} new tweets (had {len(existing_tweet_ids)} existing)"
                            )
                    all_valid_tweets.extend(unique_tweets)
                else:
                    bt.logging.info(
                        f"Miner {uid}: Validation success rate too low, not crediting tweets"
                    )
                    self.validator.scorer.add_volume(uid_int, 0, current_block)

            except Exception as e:
                bt.logging.error(f"Error processing miner {uid}: {e}")
                if uid_int:
                    self.validator.scorer.add_volume(uid_int, 0, current_block)
                continue

        return all_valid_tweets

    def _log_validation_failure(self, uid, tweet, query_words, reason):
        """Log tweet validation failure details."""
        bt.logging.info(
            f"ℹ️ [DRY RUN] Miner {uid}: Tweet validation would fail - {reason}"
        )
        bt.logging.info(
            f"ℹ️ [DRY RUN] Miner {uid}: URL=https://x.com/i/status/{tweet.get('ID')}"
        )

        if reason == "content":
            bt.logging.info(
                f"ℹ️ [DRY RUN] Miner {uid}: Query terms={', '.join(query_words)}"
            )
            bt.logging.info(
                f"ℹ️ [DRY RUN] Miner {uid}: Text={self.normalize_whitespace(tweet.get('Text', ''))}"
            )
            bt.logging.info(
                f"ℹ️ [DRY RUN] Miner {uid}: Hashtags={tweet.get('Hashtags')}"
            )
        elif reason == "timestamp":
            bt.logging.info(
                f"ℹ️ [DRY RUN] Miner {uid}: Tweet timestamp={datetime.fromtimestamp(tweet.get('Timestamp', 0), UTC)}"
            )
            bt.logging.info(
                f"ℹ️ [DRY RUN] Miner {uid}: Required after={datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)}"
            )

    def check_tempo(self, current_block: int) -> bool:
        if self.validator.last_tempo_block == 0:
            self.validator.last_tempo_block = current_block
            return True

        blocks_since_last_check = current_block - self.validator.last_tempo_block
        if blocks_since_last_check >= self.validator.tempo:
            self.validator.last_tempo_block = current_block
            return True
        else:
            return False

    def normalize_whitespace(self, s: str) -> str:
        """Normalize and truncate text for logging."""
        if not s:
            return ""
        # Replace newlines with spaces and collapse multiple spaces
        normalized = " ".join(s.split())
        # Truncate to 30 chars if longer
        if len(normalized) > 30:
            return normalized[:30] + "..."
        return normalized

    def format_miner_link(self, uid: int) -> str:
        """Format a miner's hotkey into a taostats URL."""
        hotkey = self.validator.metagraph.hotkeys[uid]
        return f"https://taostats.io/hotkey/{hotkey}"

    def format_tweet_url(self, tweet_id: str) -> str:
        """Format a tweet ID into an x.com URL."""
        return f"https://x.com/i/status/{tweet_id}"

    async def process_response(self, uid: int, response: Any) -> None:
        """Process a single miner's response."""
        try:
            # Spot check validation
            if await self.validate_spot_check(uid, response):
                bt.logging.debug(
                    f"Miner {self.format_miner_link(uid)} passed spot check"
                )

                # Process tweet counts
                if len(response.get("tweets", [])) > 0:
                    new_tweets = len(
                        [t for t in response["tweets"] if self.is_new_tweet(t)]
                    )
                    total_tweets = len(response["tweets"])

                    if new_tweets == total_tweets:
                        bt.logging.debug(
                            f"Miner {uid} produced {new_tweets} new tweets\n"
                            f"    {self.format_miner_link(uid)}"
                        )
                    else:
                        bt.logging.debug(
                            f"Miner {uid} produced {new_tweets} new tweets (total: {total_tweets})\n"
                            f"    {self.format_miner_link(uid)}"
                        )

                    # Log sample tweet URL at debug level
                    if response["tweets"]:
                        sample_tweet = response["tweets"][0]
                        bt.logging.debug(
                            f"Sample tweet from miner {self.format_miner_link(uid)}: {self.format_tweet_url(sample_tweet['id'])}"
                        )
            else:
                bt.logging.debug(
                    f"Miner {self.format_miner_link(uid)} failed spot check"
                )

        except Exception as e:
            bt.logging.error(
                f"Error processing response from miner {self.format_miner_link(int(uid))}: {e}"
            )

    async def validate_spot_check(self, uid: int, response: Any) -> bool:
        """Validate a random tweet from the response."""
        try:
            if not response or not response.get("tweets"):
                return False

            random_tweet = random.choice(response["tweets"])
            tweet_id = random_tweet.get("id")

            try:
                with SilentOutput():
                    is_valid = tweet_validator.validate_tweet(
                        random_tweet.get("ID"),
                        random_tweet.get("Name"),
                        random_tweet.get("Username"),
                        random_tweet.get("Text"),
                        random_tweet.get("Timestamp"),
                        random_tweet.get("Hashtags", []),
                    )
            except Exception as e:
                bt.logging.error(f"Validation error in spot check: {e}")
                return False

            if is_valid:
                bt.logging.info(
                    f"Tweet validation passed: {self.format_tweet_url(tweet_id)}"
                )
            else:
                bt.logging.info(
                    f"Tweet validation failed: {self.format_tweet_url(tweet_id)}"
                )

            return is_valid

        except Exception as e:
            bt.logging.error(
                f"Error in spot check for miner {self.format_miner_link(int(uid))}: {e}"
            )
            return False
