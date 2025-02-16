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

        async with bt.dendrite(wallet=self.validator.wallet) as dendrite:
            responses = await dendrite(
                [self.validator.metagraph.axons[uid] for uid in miner_uids],
                request,
                deserialize=True,
                timeout=timeout,
            )

            formatted_responses = [
                {"uid": int(uid), "response": response}
                for uid, response in zip(miner_uids, responses)
            ]
            return formatted_responses, miner_uids

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
        if len(self.validator.versions) == 0:
            bt.logging.info("🔍 Pinging axons to get miner versions...")
            return await self.ping_axons(current_block)
        if len(self.validator.keywords) == 0 or self.check_tempo(current_block):
            await self.fetch_twitter_queries()

        random_keyword = random.choice(self.validator.keywords)
        query = f'"{random_keyword.strip()}"'
        bt.logging.info(f"🔍 Volume checking for: {query}")
        request = RecentTweetsSynapse(
            query=query,
            timeout=self.validator.subnet_config.get("synthetic").get("timeout"),
        )

        responses, miner_uids = await self.forward_request(
            request,
            sample_size=self.validator.subnet_config.get("synthetic").get(
                "sample_size"
            ),
            timeout=self.validator.subnet_config.get("synthetic").get("timeout"),
            sequential=True,
        )

        bt.logging.info("Selected miners to query")
        bt.logging.info(f"Selected UIDs: {miner_uids}")

        all_valid_tweets = []
        validator = None
        with SilentOutput():
            validator = TweetValidator()

        for response, uid in zip(responses, miner_uids):
            try:
                valid_tweets = []
                all_responses = dict(response).get("response", [])
                if not all_responses:
                    continue

                # First filter out any tweets with non-numeric IDs and log bad miners
                valid_tweet_count = 0
                invalid_tweet_count = 0
                invalid_ids = []
                for tweet in all_responses:
                    if (
                        "Tweet" in tweet
                        and "ID" in tweet["Tweet"]
                        and tweet["Tweet"]["ID"]
                    ):
                        tweet_id = tweet["Tweet"]["ID"].strip()
                        if tweet_id.isdigit():
                            valid_tweets.append(tweet)
                            valid_tweet_count += 1
                        else:
                            invalid_ids.append(tweet_id)
                            invalid_tweet_count += 1
                    else:
                        invalid_tweet_count += 1

                if invalid_tweet_count > 0:
                    bt.logging.info(
                        f"❌ Miner {uid} penalized - submitted {invalid_tweet_count} tweets with invalid IDs out of {len(all_responses)}"
                    )
                    if invalid_ids:
                        bt.logging.debug(
                            f"❌ Invalid IDs from miner {uid}: {invalid_ids[:5]}..."
                        )
                    # Give zero score for submitting any invalid tweets
                    self.validator.scorer.add_volume(int(uid), 0, current_block)
                    continue

                # Deduplicate valid tweets using numeric IDs
                unique_tweets_response = list(
                    {tweet["Tweet"]["ID"]: tweet for tweet in valid_tweets}.values()
                )

                if not unique_tweets_response:
                    bt.logging.debug(
                        f"Miner {self.format_miner_link(int(uid))} had no valid tweets after filtering"
                    )
                    continue

                # Validate a random tweet from the valid set
                random_tweet = dict(random.choice(unique_tweets_response)).get(
                    "Tweet", {}
                )

                validation_response = None
                try:
                    validation_response = validator.validate_tweet(
                        random_tweet.get("ID"),
                        random_tweet.get("Name"),
                        random_tweet.get("Username"),
                        random_tweet.get("Text"),
                        random_tweet.get("Timestamp"),
                        random_tweet.get("Hashtags"),
                    )

                    # Detailed validation logging
                    validation_details = {
                        "tweet_id": random_tweet.get("ID"),
                        "text_length": len(random_tweet.get("Text", "")),
                        "timestamp": datetime.fromtimestamp(
                            random_tweet.get("Timestamp", 0), UTC
                        ),
                        "query_terms": query_words,
                        "found_in_fields": {
                            "text": any(
                                word
                                in self.normalize_whitespace(
                                    random_tweet.get("Text", "")
                                )
                                .strip()
                                .lower()
                                for word in query_words
                            ),
                            "name": any(
                                word
                                in self.normalize_whitespace(
                                    random_tweet.get("Name", "")
                                )
                                .strip()
                                .lower()
                                for word in query_words
                            ),
                            "username": any(
                                word
                                in self.normalize_whitespace(
                                    random_tweet.get("Username", "")
                                )
                                .strip()
                                .lower()
                                for word in query_words
                            ),
                            "hashtags": any(
                                word
                                in self.normalize_whitespace(
                                    str(random_tweet.get("Hashtags", []))
                                )
                                .strip()
                                .lower()
                                for word in query_words
                            ),
                        },
                    }

                    bt.logging.debug(
                        f"Miner {uid}: Validation details for {self.format_tweet_url(random_tweet.get('ID'))}:\n"
                        f"    Response: {validation_response}\n"
                        f"    Tweet text: {random_tweet.get('Text')[:100]}...\n"
                        f"    Timestamp: {validation_details['timestamp']}\n"
                        f"    Query terms: {', '.join(validation_details['query_terms'])}\n"
                        f"    Found in:\n"
                        f"      - Text: {'✅' if validation_details['found_in_fields']['text'] else '❌'}\n"
                        f"      - Name: {'✅' if validation_details['found_in_fields']['name'] else '❌'}\n"
                        f"      - Username: {'✅' if validation_details['found_in_fields']['username'] else '❌'}\n"
                        f"      - Hashtags: {'✅' if validation_details['found_in_fields']['hashtags'] else '❌'}"
                    )
                except Exception as e:
                    error_str = str(e)
                    bt.logging.debug(
                        f"Miner {uid}: Connection/validation issue for {self.format_tweet_url(random_tweet.get('ID'))}:\n"
                        f"    Error: {error_str}\n"
                        f"    Tweet ID: {random_tweet.get('ID')}\n"
                        f"    Timestamp: {datetime.fromtimestamp(random_tweet.get('Timestamp', 0), UTC)}"
                    )
                    # Don't count external validation issues as failures
                    validation_response = None

                # Check content requirements first
                query_words = (
                    self.normalize_whitespace(random_keyword.replace('"', ""))
                    .strip()
                    .lower()
                    .split()
                )
                fields_to_check = [
                    self.normalize_whitespace(random_tweet.get("Text", ""))
                    .strip()
                    .lower(),
                    self.normalize_whitespace(random_tweet.get("Name", ""))
                    .strip()
                    .lower(),
                    self.normalize_whitespace(random_tweet.get("Username", ""))
                    .strip()
                    .lower(),
                    self.normalize_whitespace(str(random_tweet.get("Hashtags", [])))
                    .strip()
                    .lower(),
                ]
                query_in_tweet = any(
                    any(word in field for field in fields_to_check)
                    for word in query_words
                )

                tweet_timestamp = datetime.fromtimestamp(
                    random_tweet.get("Timestamp", 0), UTC
                )
                yesterday = datetime.now(UTC).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) - timedelta(days=1)
                is_since_date_requested = yesterday <= tweet_timestamp

                # Only consider it a true failure if content requirements aren't met
                if not query_in_tweet:
                    bt.logging.info(
                        f"❌ Miner {uid}: Tweet validation failed - Query terms not found"
                    )
                    bt.logging.info(
                        f"❌ Miner {uid}: URL=https://x.com/i/status/{random_tweet.get('ID')}"
                    )
                    bt.logging.info(
                        f"❌ Miner {uid}: Query terms={', '.join(query_words)}"
                    )
                    bt.logging.info(
                        f"❌ Miner {uid}: Text={self.normalize_whitespace(random_tweet.get('Text', ''))}"
                    )
                    bt.logging.info(f"❌ Miner {uid}: Name={random_tweet.get('Name')}")
                    bt.logging.info(
                        f"❌ Miner {uid}: Username={random_tweet.get('Username')}"
                    )
                    bt.logging.info(
                        f"❌ Miner {uid}: Hashtags={random_tweet.get('Hashtags')}"
                    )
                    self.validator.scorer.add_volume(int(uid), 0, current_block)
                    continue
                elif not is_since_date_requested:
                    bt.logging.info(
                        f"❌ Miner {uid}: Tweet validation failed - Tweet too old"
                    )
                    bt.logging.info(
                        f"❌ Miner {uid}: URL=https://x.com/i/status/{random_tweet.get('ID')}"
                    )
                    bt.logging.info(
                        f"❌ Miner {uid}: Tweet timestamp={tweet_timestamp}"
                    )
                    bt.logging.info(f"❌ Miner {uid}: Required after={yesterday}")
                    self.validator.scorer.add_volume(int(uid), 0, current_block)
                    continue
                elif validation_response is False:
                    # Log the failure but don't penalize unless we're certain
                    bt.logging.info(
                        f"⚠️ Miner {uid}: External validation check failed but content valid"
                    )
                    bt.logging.info(
                        f"⚠️ Miner {uid}: URL=https://x.com/i/status/{random_tweet.get('ID')}"
                    )
                    bt.logging.info(
                        f"⚠️ Miner {uid}: Text={self.normalize_whitespace(random_tweet.get('Text', ''))}"
                    )
                    bt.logging.info(f"⚠️ Miner {uid}: Timestamp={tweet_timestamp}")
                elif validation_response is None:
                    bt.logging.info(f"⚠️ Miner {uid}: External validation skipped")
                    bt.logging.info(
                        f"⚠️ Miner {uid}: URL=https://x.com/i/status/{random_tweet.get('ID')}"
                    )
                    bt.logging.info(
                        f"⚠️ Miner {uid}: Text={self.normalize_whitespace(random_tweet.get('Text', ''))}"
                    )
                else:
                    bt.logging.info(f"✅ Miner {uid}: Tweet validation passed")
                    bt.logging.info(
                        f"✅ Miner {uid}: URL=https://x.com/i/status/{random_tweet.get('ID')}"
                    )
                    bt.logging.info(
                        f"✅ Miner {uid}: Query terms found in={[field for field, found in validation_details['found_in_fields'].items() if found]}"
                    )
                    bt.logging.info(
                        f"✅ Miner {uid}: Text={self.normalize_whitespace(random_tweet.get('Text', ''))}"
                    )

                # If we get here, the tweet passed our core validation
                all_valid_tweets.extend(unique_tweets_response)

            except Exception as e:
                bt.logging.error(
                    f"Error processing miner {self.format_miner_link(int(uid))}: {e}"
                )
                continue

        # Send tweets to API
        await self.validator.export_tweets(
            list({tweet["Tweet"]["ID"]: tweet for tweet in all_valid_tweets}.values()),
            query.strip().replace('"', ""),
        )

        self.validator.last_volume_block = current_block

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

            is_valid = await self.validate_tweet(random_tweet)

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

    async def retry_pending_validations(self, current_block: int):
        """Retry validation for pending tweets."""
        if not self.validator.pending_validations:
            return

        bt.logging.info(
            f"🔄 Retrying validation for {len(self.validator.pending_validations)} miners' tweets"
        )

        validator = None
        with SilentOutput():
            validator = TweetValidator()

        for uid, pending_tweets in list(self.validator.pending_validations.items()):
            valid_tweets = []
            for tweet_id, tweet_data in list(pending_tweets.items()):
                # Skip if we tried too recently
                blocks_since_last_attempt = current_block - tweet_data.get(
                    "last_attempt", 0
                )
                if blocks_since_last_attempt < 100:  # Wait ~20 minutes between retries
                    continue

                # Skip if we've tried too many times
                if tweet_data.get("attempts", 0) >= 3:
                    bt.logging.debug(
                        f"❌ Giving up on tweet after 3 attempts: {self.format_tweet_url(tweet_id)}"
                    )
                    pending_tweets.pop(tweet_id)
                    continue

                try:
                    tweet = tweet_data["tweet"]
                    validation_response = validator.validate_tweet(
                        tweet.get("ID"),
                        tweet.get("Name"),
                        tweet.get("Username"),
                        tweet.get("Text"),
                        tweet.get("Timestamp"),
                        tweet.get("Hashtags"),
                    )

                    if validation_response:
                        bt.logging.info(
                            f"Miner {uid}: ✅ Retry validation passed: {self.format_tweet_url(tweet_id)}"
                        )
                        valid_tweets.append(tweet)
                        pending_tweets.pop(tweet_id)
                    else:
                        # Update attempt count and timestamp
                        tweet_data["attempts"] = tweet_data.get("attempts", 0) + 1
                        tweet_data["last_attempt"] = current_block
                        bt.logging.debug(
                            f"Miner {uid}: ❌ Retry validation failed: {self.format_tweet_url(tweet_id)}"
                        )

                except Exception as e:
                    error_str = str(e)
                    tweet_data["attempts"] = tweet_data.get("attempts", 0) + 1
                    tweet_data["last_attempt"] = current_block

                    if "429" in error_str or "Too Many Requests" in error_str:
                        bt.logging.debug(
                            f"❓ Still rate limited for: {self.format_tweet_url(tweet_id)}"
                        )
                    elif "ServerDisconnectedError" in error_str:
                        bt.logging.debug(
                            f"📡 Server still disconnected for: {self.format_tweet_url(tweet_id)}"
                        )
                    else:
                        bt.logging.debug(
                            f"⚠️ Retry error for {self.format_tweet_url(tweet_id)}: {error_str}"
                        )

                await asyncio.sleep(2)  # Rate limiting protection

            # If we validated any tweets, update the miner's score
            if valid_tweets:
                if not self.validator.tweets_by_uid.get(uid):
                    self.validator.tweets_by_uid[uid] = {
                        tweet["ID"] for tweet in valid_tweets
                    }
                else:
                    self.validator.tweets_by_uid[uid].update(
                        {tweet["ID"] for tweet in valid_tweets}
                    )

                self.validator.scorer.add_volume(uid, len(valid_tweets), current_block)
                bt.logging.info(
                    f"📈 Added {len(valid_tweets)} validated tweets for miner {self.format_miner_link(int(uid))}"
                )

            # Clean up if no more pending tweets for this miner
            if not pending_tweets:
                self.validator.pending_validations.pop(uid)
