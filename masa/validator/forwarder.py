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
from typing import Any, List
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
from masa.utils.uids import (
    get_random_miner_uids,
    get_uncalled_miner_uids,
    get_available_uids,
)

# Import our new validator
from masa.validator.tweet_validator import TweetValidator as ProtocolTweetValidator

# Used only for trending queries functionality
from masa_ai.tools.validator import TrendingQueries

import re
import sys
import os


class Forwarder:
    def __init__(self, validator):
        self.validator = validator

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
        summary_parts = [f"Miners: {reachable}/{total_miners} online"]

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
        miner_uids = list(
            self.validator.uncalled_uids
        )  # Convert set to list for indexing
        total_miners = len(miner_uids)
        successful_pings = 0
        failed_pings = 0

        bt.logging.info(
            f"Starting to ping {total_miners} miners in batches of {sample_size}"
        )

        async with bt.dendrite(wallet=self.validator.wallet) as dendrite:
            for i in range(0, total_miners, sample_size):
                batch_uids = miner_uids[i : i + sample_size]
                batch = [self.validator.metagraph.axons[uid] for uid in batch_uids]
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

        self.validator.versions = [response.version for response in all_responses]

        # Use the summarize function for a cleaner log
        version_summary = self._summarize_versions(self.validator.versions)
        bt.logging.info(f"🔍 Miner Status: {version_summary}")

        # Keep detailed version list at DEBUG level
        bt.logging.debug(f"Detailed Miner Versions: {self.validator.versions}")

        self.validator.last_healthcheck_block = current_block
        return [
            {
                "status_code": response.dendrite.status_code,
                "status_message": response.dendrite.status_message,
                "version": response.version,
                "uid": miner_uids[all_responses.index(response)],  # Use actual UID
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

    async def fetch_subnet_config(self):
        async with aiohttp.ClientSession() as session:
            url = "https://raw.githubusercontent.com/masa-finance/masa-bittensor/main/config.json"
            network_type = (
                "testnet"
                if self.validator.config.subtensor.network == "test"
                else "mainnet"
            )
            async with session.get(url) as response:
                if response.status == 200:
                    configRaw = await response.text()
                    config = json.loads(configRaw)
                    subnet_config = config.get(network_type, {})
                    bt.logging.info(
                        f"fetched {network_type} config from github: {subnet_config}"
                    )
                    self.validator.subnet_config = subnet_config
                else:
                    bt.logging.error(
                        f"failed to fetch subnet config from GitHub: {response.status}"
                    )

    async def get_miners_volumes(self, current_block: int):
        if len(self.validator.versions) == 0:
            bt.logging.info("Pinging axons to get miner versions...")
            return await self.ping_axons(current_block)
        if len(self.validator.keywords) == 0 or self.check_tempo(current_block):
            await self.fetch_twitter_queries()
        if len(self.validator.subnet_config) == 0 or self.check_tempo(current_block):
            await self.fetch_subnet_config()

        # Reset uncalled_uids if empty
        if len(self.validator.uncalled_uids) == 0:
            bt.logging.info("Resetting uncalled UIDs pool with all available miners...")
            # Generic sanitation
            avail_uids = get_available_uids(self.validator.metagraph)
            subnet_params = await self.validator.subtensor.get_subnet_hyperparameters(
                self.validator.config.netuid
            )
            weights_version = subnet_params.weights_version

            # Ensure versions list is properly sized
            if len(self.validator.versions) < self.validator.metagraph.n.item():
                self.validator.versions = [0] * self.validator.metagraph.n.item()

            version_checked_uids = [
                uid
                for uid in avail_uids
                if uid < len(self.validator.versions)
                and self.validator.versions[uid] >= weights_version
            ]
            self.validator.uncalled_uids = set(version_checked_uids)
            bt.logging.info(
                f"Reset pool with {len(self.validator.uncalled_uids)} miners"
            )

        random_keyword = random.choice(self.validator.keywords)
        query = f'"{random_keyword.strip()}"'
        bt.logging.info(f"Volume checking for: {query}")
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

        all_valid_tweets = []
        validator = (
            ProtocolTweetValidator()
        )  # Use our new validator that hits the protocol API

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
                        tweet_id = tweet["Tweet"]["ID"]
                        if tweet_id.isdigit():  # Must be purely numeric
                            valid_tweets.append(tweet)
                            valid_tweet_count += 1
                        else:
                            invalid_ids.append(tweet_id)
                            invalid_tweet_count += 1
                    else:
                        invalid_tweet_count += 1

                if invalid_tweet_count > 0:
                    bt.logging.info(
                        f"❌ {self.format_miner_info(int(uid))} FAILED ID validation - {invalid_tweet_count} invalid tweets out of {len(all_responses)}"
                    )
                    # Give zero score for submitting any invalid tweets
                    self.validator.scorer.add_volume(int(uid), 0, current_block)
                    continue  # Skip further processing for this miner
                else:
                    bt.logging.info(
                        f"✅ {self.format_miner_info(int(uid))} PASSED ID validation - all {valid_tweet_count} tweets had valid IDs"
                    )

                # Deduplicate valid tweets using numeric IDs
                unique_tweets_response = list(
                    {tweet["Tweet"]["ID"]: tweet for tweet in valid_tweets}.values()
                )

                if not unique_tweets_response:  # If no valid tweets after filtering
                    bt.logging.debug(f"Miner {uid} had no valid tweets after filtering")
                    continue

                # Continue with validation of a random tweet from the valid set
                random_tweet = dict(random.choice(unique_tweets_response)).get(
                    "Tweet", {}
                )

                # Validate tweet using our new validator
                validation_result = await validator.validate_tweet(
                    random_tweet.get("ID"),
                    random_tweet.get("Name"),
                    random_tweet.get("Username"),
                    random_tweet.get("Text"),
                    random_tweet.get("Timestamp"),
                    random_tweet.get("Hashtags", []),
                )

                # Always wait at least 2 seconds between validations to avoid rate limits
                await asyncio.sleep(2)

                # Determine validation status
                if validation_result:
                    bt.logging.info(
                        f"✅ Tweet verified via protocol API: {self.format_tweet_url(random_tweet.get('ID'))}"
                    )
                    is_valid = True
                else:
                    bt.logging.info(
                        f"❌ Tweet validation failed via protocol API: {self.format_tweet_url(random_tweet.get('ID'))}"
                    )
                    is_valid = False

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

                query_in_tweet = all(
                    any(word in field for field in fields_to_check)
                    for word in query_words
                )

                if not query_in_tweet:
                    bt.logging.debug(
                        f"Query match check failed for {self.format_tweet_url(random_tweet.get('ID'))}"
                    )

                tweet_timestamp = datetime.fromtimestamp(
                    random_tweet.get("Timestamp", 0), UTC
                )

                yesterday = datetime.now(UTC).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) - timedelta(days=1)
                is_since_date_requested = yesterday <= tweet_timestamp

                if not is_since_date_requested:
                    bt.logging.debug(
                        f"Tweet timestamp check failed for {self.format_tweet_url(random_tweet.get('ID'))}"
                    )

                # note, they passed the spot check!
                if is_valid and query_in_tweet and is_since_date_requested:
                    bt.logging.info(
                        f"✅ Tweet verified on Twitter: {self.format_tweet_url(random_tweet.get('ID'))}"
                    )
                    for tweet in unique_tweets_response:
                        if tweet:
                            valid_tweets.append(tweet)
                else:
                    failures = []
                    if not is_valid:
                        failures.append("masa-api verification")
                    if not query_in_tweet:
                        failures.append("query match")
                    if not is_since_date_requested:
                        failures.append("timestamp")
                    bt.logging.info(
                        f"❌ Tweet validation failed ({', '.join(failures)}): {self.format_tweet_url(random_tweet.get('ID'))}"
                    )

                all_valid_tweets.extend(valid_tweets)

                # note, score only unique tweets per miner (uid)
                uid_int = int(uid)

                if not self.validator.tweets_by_uid.get(uid_int):
                    self.validator.tweets_by_uid[uid_int] = {
                        tweet["Tweet"]["ID"] for tweet in valid_tweets
                    }
                    self.validator.scorer.add_volume(
                        uid_int, len(valid_tweets), current_block
                    )
                    bt.logging.debug(
                        f"Miner {uid_int} produced {len(valid_tweets)} new tweets"
                    )
                else:
                    existing_tweet_ids = self.validator.tweets_by_uid[uid_int]
                    new_tweet_ids = {tweet["Tweet"]["ID"] for tweet in valid_tweets}
                    updates = new_tweet_ids - existing_tweet_ids
                    self.validator.tweets_by_uid[uid_int].update(new_tweet_ids)
                    self.validator.scorer.add_volume(
                        uid_int, len(updates), current_block
                    )
                    bt.logging.debug(
                        f"Miner {uid_int} produced {len(updates)} new tweets"
                    )
            except Exception as e:
                bt.logging.error(f"Error processing miner {uid}: {e}")
                continue

        # Send tweets to API
        await self.validator.export_tweets(
            list({tweet["Tweet"]["ID"]: tweet for tweet in all_valid_tweets}.values()),
            query.strip().replace('"', ""),
        )

        # note, set the last volume block to the current block
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
        return " ".join(s.split())

    def format_tweet_url(self, tweet_id: str) -> str:
        """Format a tweet ID into an x.com URL."""
        return f"https://x.com/i/status/{tweet_id}"

    async def process_response(self, uid: int, response: Any) -> None:
        """Process a single miner's response."""
        try:
            # Spot check validation
            if await self.validate_spot_check(uid, response):
                bt.logging.debug(f"Miner {uid} passed spot check")

                # Process tweet counts
                if len(response.get("tweets", [])) > 0:
                    new_tweets = len(
                        [t for t in response["tweets"] if self.is_new_tweet(t)]
                    )
                    total_tweets = len(response["tweets"])

                    if new_tweets == total_tweets:
                        bt.logging.debug(
                            f"Miner {uid} produced {new_tweets} new tweets"
                        )
                    else:
                        bt.logging.debug(
                            f"Miner {uid} produced {new_tweets} new tweets (total: {total_tweets})"
                        )

                    # Log sample tweet URL at debug level
                    if response["tweets"]:
                        sample_tweet = response["tweets"][0]
                        bt.logging.debug(
                            f"Sample tweet from miner {uid}: {self.format_tweet_url(sample_tweet['id'])}"
                        )
            else:
                bt.logging.debug(f"Miner {uid} failed spot check")

        except Exception as e:
            bt.logging.error(f"Error processing response from miner {uid}: {e}")

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
            bt.logging.error(f"Error in spot check for miner {uid}: {e}")
            return False

    # Helper function to format miner info
    def format_miner_info(self, uid: int) -> str:
        """Format miner info with TaoStats link using hotkey."""
        try:
            hotkey = self.validator.metagraph.hotkeys[uid]
            return f"Miner {uid} (https://taostats.io/hotkey/{hotkey})"
        except (IndexError, AttributeError):
            # Fallback if we can't get the hotkey for some reason
            return f"Miner {uid}"
