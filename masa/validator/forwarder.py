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

# Used only for trending queries functionality
from masa_ai.tools.validator import TrendingQueries, TweetValidator

import re
import sys
import os


class Forwarder:
    def __init__(self, validator):
        self.validator = validator

    def strict_tweet_id_validation(self, tweet_id: str) -> bool:
        """
        Strictly validate a tweet ID.
        - Must be a string of pure ASCII digits
        - No leading zeros
        - No invisible/zero-width characters
        """
        if not isinstance(tweet_id, str):
            return False

        # Convert to ASCII-only and check if anything was removed
        ascii_id = tweet_id.encode("ascii", "ignore").decode()
        if ascii_id != tweet_id:
            return False

        # Check if it's a valid numeric string with no leading zeros
        if not ascii_id.isdigit() or ascii_id.startswith("0"):
            return False

        return True

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

        bt.logging.debug(f"Request timeout set to {timeout}s with no retries")

        if sequential:
            miner_uids = await get_uncalled_miner_uids(self.validator, k=sample_size)
        else:
            miner_uids = await get_random_miner_uids(self.validator, k=sample_size)

        if miner_uids is None or len(miner_uids) == 0:
            return [], []

        async with bt.dendrite(wallet=self.validator.wallet) as dendrite:
            bt.logging.debug(
                f"Sending request to {len(miner_uids)} miners with {timeout}s timeout"
            )
            try:
                responses = await dendrite(
                    [self.validator.metagraph.axons[uid] for uid in miner_uids],
                    request,
                    deserialize=True,
                    timeout=timeout,
                )
            except Exception as e:
                bt.logging.error(f"Dendrite request failed: {e}")
                return [], []

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
        miner_uids = get_available_uids(self.validator.metagraph)
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

    async def validate_tweet_batch(
        self, uid: int, all_responses: list, random_keyword: str
    ) -> bool:
        """
        Validate a batch of tweets from a miner. Performs all validation checks in sequence:
        1. Basic structure and ID validation
        2. Duplicate detection within batch
        3. Query matching
        4. Timestamp validation
        5. Existence verification via masa-ai

        Returns True only if ALL validation checks pass.
        """
        try:
            # Flag to track if all tweets passed validation
            all_tweets_valid = True

            # Create TweetValidator instance from masa-ai package
            validator = TweetValidator()

            # Validate all tweets first for basic structure
            for i, tweet in enumerate(all_responses, 1):
                if not (
                    "Tweet" in tweet and "ID" in tweet["Tweet"] and tweet["Tweet"]["ID"]
                ):
                    bt.logging.info(
                        f"❌ {self.format_miner_info(uid)} FAILED - malformed tweet at position {i}/{len(all_responses)} | Tweet: {tweet}"
                    )
                    all_tweets_valid = False
                    break  # Break inner loop

                tweet_id = tweet["Tweet"]["ID"]
                if not self.strict_tweet_id_validation(tweet_id):
                    bt.logging.info(
                        f"❌ {self.format_miner_info(uid)} FAILED - invalid tweet ID at position {i}/{len(all_responses)} | ID: {tweet_id}\n"
                        f"    Tweet Text: {tweet['Tweet'].get('Text', 'NO_TEXT')}\n"
                        f"    Full Tweet: {tweet}"
                    )
                    all_tweets_valid = False
                    break  # Break inner loop

            # Check for duplicates
            unique_ids = {tweet["Tweet"]["ID"] for tweet in all_responses}
            if len(unique_ids) != len(all_responses):
                bt.logging.info(
                    f"❌ {self.format_miner_info(uid)} FAILED - batch contains duplicates"
                )
                all_tweets_valid = False
                return False

            # Select 3 random tweets for validation
            num_tweets_to_validate = min(3, len(all_responses))
            random_tweets = random.sample(all_responses, num_tweets_to_validate)

            # Validate each selected tweet
            for i, tweet_data in enumerate(random_tweets, 1):
                random_tweet = dict(tweet_data).get("Tweet", {})
                random_tweet_id = random_tweet.get("ID")
                bt.logging.info(f"Selected tweet {random_tweet_id} for validation")

                # Add detailed logging of the sample tweet
                bt.logging.info(
                    f"\n🔍 Sample Tweet Validation Details for {self.format_miner_info(uid)}:\n"
                    f"    ID: {random_tweet.get('ID')}\n"
                    f"    Text: {random_tweet.get('Text', 'NO_TEXT')}\n"
                    f"    Username: {random_tweet.get('Username', 'NO_USERNAME')}\n"
                    f"    Name: {random_tweet.get('Name', 'NO_NAME')}\n"
                    f"    Timestamp: {datetime.fromtimestamp(random_tweet.get('Timestamp', 0), UTC)}\n"
                    f"    URL: {self.format_tweet_url(random_tweet.get('ID'))}"
                )

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
                    bt.logging.info(
                        f"❌ Query match check failed for {self.format_tweet_url(random_tweet.get('ID'))}"
                    )
                    all_tweets_valid = False

                tweet_timestamp = datetime.fromtimestamp(
                    random_tweet.get("Timestamp", 0), UTC
                )

                yesterday = datetime.now(UTC).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) - timedelta(days=1)
                is_since_date_requested = yesterday <= tweet_timestamp

                if not is_since_date_requested:
                    bt.logging.debug(
                        f"❌ Timestamp check failed for {self.format_tweet_url(random_tweet.get('ID'))}"
                    )
                    all_tweets_valid = False

                # Log validation results for both checks
                tweet_url = self.format_tweet_url(random_tweet.get("ID"))
                bt.logging.info(
                    f"{'✅' if query_in_tweet else '❌'} Query match ({random_keyword}): {tweet_url}"
                )
                bt.logging.info(
                    f"{'✅' if is_since_date_requested else '❌'} Timestamp ({tweet_timestamp.strftime('%Y-%m-%d %H:%M:%S')} >= {yesterday.strftime('%Y-%m-%d')}): {tweet_url}"
                )

                # Only proceed with masa-ai validation if other checks passed
                if all_tweets_valid:
                    try:
                        # Make 3 attempts at masa-ai validation
                        validation_attempts = 0
                        successful_validations = 0

                        for attempt in range(3):
                            validation_attempts += 1
                            try:
                                # Validate with masa-ai's TweetValidator
                                bt.logging.info(
                                    f"🔍 Attempting to validate tweet {random_tweet.get('ID')} with masa-ai validator (attempt {attempt + 1}/3)"
                                )
                                bt.logging.info(
                                    f"📤 Sending to masa-ai for validation:\n"
                                    f"    tweet_id: {random_tweet.get('ID')}\n"
                                    f"    expected_name: {random_tweet.get('Name')}\n"
                                    f"    expected_username: {random_tweet.get('Username')}\n"
                                    f"    expected_text: {random_tweet.get('Text')}\n"
                                    f"    expected_timestamp: {random_tweet.get('Timestamp')}\n"
                                    f"    expected_hashtags: {random_tweet.get('Hashtags', [])}"
                                )
                                try:
                                    is_valid = validator.validate_tweet(
                                        tweet_id=random_tweet.get("ID"),
                                        expected_name=random_tweet.get("Name"),
                                        expected_username=random_tweet.get("Username"),
                                        expected_text=random_tweet.get("Text"),
                                        expected_timestamp=random_tweet.get(
                                            "Timestamp"
                                        ),
                                        expected_hashtags=random_tweet.get(
                                            "Hashtags", []
                                        ),
                                    )
                                    if is_valid:
                                        successful_validations += 1
                                        bt.logging.info(
                                            f"✅ Tweet {tweet_url} passed masa-ai validation on attempt {attempt + 1}"
                                        )
                                    else:
                                        bt.logging.info(
                                            f"❌ Tweet {tweet_url} failed masa-ai validation on attempt {attempt + 1}"
                                        )
                                except Exception as validation_error:
                                    error_msg = str(validation_error)
                                    if "404" in error_msg:
                                        bt.logging.info(
                                            f"❌ Tweet {tweet_url} received 404 from Twitter API on attempt {attempt + 1}"
                                        )
                                    else:
                                        bt.logging.info(
                                            f"❓ Tweet {tweet_url} encountered technical error on attempt {attempt + 1}: {validation_error}"
                                        )
                                        successful_validations += 1

                            except Exception as e:
                                error_msg = str(e)
                                if "404" in error_msg:
                                    bt.logging.info(
                                        f"❌ Tweet {tweet_url} received 404 from Twitter API on attempt {attempt + 1}"
                                    )
                                else:
                                    bt.logging.info(
                                        f"❓ Tweet {tweet_url} encountered technical error on attempt {attempt + 1}: {e}"
                                    )
                                    successful_validations += 1

                            # Add a delay between attempts (3 seconds)
                            if attempt < 2:  # Don't delay after the last attempt
                                bt.logging.info(
                                    "Waiting 3 seconds before next validation attempt..."
                                )
                                await asyncio.sleep(3)

                        # After all attempts, check if we got enough successful validations
                        if successful_validations >= 2:
                            bt.logging.info(
                                f"✅ Tweet {tweet_url} passed masa-ai validation ({successful_validations}/3 attempts successful)"
                            )
                        else:
                            bt.logging.info(
                                f"❌ Tweet {tweet_url} failed masa-ai validation (only {successful_validations}/{validation_attempts} attempts successful)"
                            )
                            all_tweets_valid = False

                    except Exception as e:
                        bt.logging.error(
                            f"Unexpected error during masa-ai validation: {e}"
                        )
                        all_tweets_valid = False

                # Add 5-second delay between validating different tweets (except for the last tweet)
                if i < num_tweets_to_validate:
                    bt.logging.info("Waiting 5 seconds before validating next tweet...")
                    await asyncio.sleep(5)

            return all_tweets_valid

        except Exception as e:
            bt.logging.error(
                f"Error validating tweets from {self.format_miner_info(uid)}: {e}"
            )
            return False

    async def get_miners_volumes(self, current_block: int):
        if len(self.validator.versions) == 0:
            bt.logging.info("Pinging axons to get miner versions...")
            return await self.ping_axons(current_block)
        if len(self.validator.keywords) == 0 or self.check_tempo(current_block):
            await self.fetch_twitter_queries()

        # Reset uncalled_uids if empty
        if len(self.validator.uncalled_uids) == 0:
            bt.logging.info("Resetting uncalled UIDs pool with all available miners...")
            # Reset to ALL miner UIDs (those with validator_trust = 0)
            miner_uids = [
                uid
                for uid in range(self.validator.metagraph.n.item())
                if self.validator.metagraph.validator_trust[uid] == 0
            ]
            self.validator.uncalled_uids = set(miner_uids)
            bt.logging.info(
                f"Reset pool with {len(self.validator.uncalled_uids)} miners"
            )

        random_keyword = random.choice(self.validator.keywords)
        query = f'"{random_keyword.strip()}"'
        bt.logging.info(f"Volume checking for: {query}")

        # Add debug logging to check the subnet_config
        bt.logging.info(f"DEBUG - subnet_config: {self.validator.subnet_config}")
        bt.logging.info(
            f"DEBUG - synthetic config: {self.validator.subnet_config.get('synthetic', {})}"
        )

        timeout = self.validator.subnet_config.get("synthetic").get("timeout")
        sample_size = self.validator.subnet_config.get("synthetic").get("sample_size")

        # Add debug logging to check the timeout and sample_size
        bt.logging.info(
            f"DEBUG - synthetic timeout: {timeout}, sample_size: {sample_size}"
        )

        bt.logging.info(
            f"Using timeout of {timeout}s for batch of {sample_size} miners"
        )

        request = RecentTweetsSynapse(
            query=query,
            timeout=timeout,
        )
        responses, miner_uids = await self.forward_request(
            request,
            sample_size=sample_size,
            timeout=timeout,
            sequential=True,
        )

        # Convert tensor UIDs to regular integers for consistent logging
        miner_uids = [int(uid) for uid in miner_uids]
        bt.logging.info(f"📋 Selected {len(miner_uids)} miners | UIDs: {miner_uids}")

        # Track different outcomes
        no_response_uids = set()
        empty_response_uids = set()
        invalid_tweet_uids = set()
        successful_uids = set()

        for response, uid in zip(responses, miner_uids):
            try:
                if not response:
                    bt.logging.info(
                        f"❌ {self.format_miner_info(uid)} FAILED - no response received | Raw: {response}"
                    )
                    no_response_uids.add(uid)
                    continue

                try:
                    all_responses = response.get("response", [])
                    bt.logging.debug(
                        f"Raw response from {self.format_miner_info(uid)}: {response}"
                    )
                except Exception as e:
                    bt.logging.info(
                        f"❌ {self.format_miner_info(uid)} FAILED - malformed response | Error: {e} | Raw: {response}"
                    )
                    empty_response_uids.add(uid)
                    continue

                if not all_responses:
                    bt.logging.info(
                        f"✅ {self.format_miner_info(uid)} returned no tweets"
                    )
                    successful_uids.add(uid)  # This is a valid response
                    continue

                bt.logging.info(
                    f"Processing {len(all_responses)} tweets from {self.format_miner_info(uid)}"
                )

                # Validate the batch
                if await self.validate_tweet_batch(uid, all_responses, random_keyword):
                    uid_int = int(uid)

                    # Handle volume scoring
                    if not self.validator.tweets_by_uid.get(uid_int):
                        self.validator.tweets_by_uid[uid_int] = {
                            tweet["Tweet"]["ID"] for tweet in all_responses
                        }
                        new_tweet_count = len(all_responses)
                        self.validator.scorer.add_volume(
                            uid_int, new_tweet_count, current_block
                        )
                        bt.logging.info(
                            f"First submission from {self.format_miner_info(uid_int)}: {new_tweet_count} new tweets"
                        )
                    else:
                        existing_tweet_ids = self.validator.tweets_by_uid[uid_int]
                        new_tweet_ids = {
                            tweet["Tweet"]["ID"] for tweet in all_responses
                        }
                        updates = new_tweet_ids - existing_tweet_ids
                        duplicate_with_history = len(new_tweet_ids) - len(updates)

                        if duplicate_with_history > 0:
                            bt.logging.info(
                                f"Found {duplicate_with_history} previously seen tweets from {self.format_miner_info(uid_int)} "
                                f"(reduced from {len(new_tweet_ids)} to {len(updates)} new tweets)"
                            )
                        else:
                            bt.logging.debug(
                                f"All {len(new_tweet_ids)} tweets from {self.format_miner_info(uid_int)} are new"
                            )

                        self.validator.tweets_by_uid[uid_int].update(new_tweet_ids)
                        self.validator.scorer.add_volume(
                            uid_int, len(updates), current_block
                        )

                    bt.logging.info(
                        f"✅ All {len(all_responses)} tweets from {self.format_miner_info(uid)} passed validation, exporting batch"
                    )

                    # DETAILED EXPORT LOGGING
                    tweet_ids = [tweet["Tweet"]["ID"] for tweet in all_responses]
                    bt.logging.info(
                        f"🚀 EXPORTING {len(all_responses)} tweets from {self.format_miner_info(uid)}"
                    )
                    # Show just the first few IDs as examples
                    sample_size = min(3, len(tweet_ids))
                    if sample_size > 0:
                        sample_ids = tweet_ids[:sample_size]
                        bt.logging.info(
                            f"Sample IDs: {sample_ids}{' + more...' if len(tweet_ids) > sample_size else ''}"
                        )

                    # Add TimeParsed field to each tweet before export
                    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                    for tweet in all_responses:
                        if "Tweet" in tweet:
                            tweet["Tweet"]["TimeParsed"] = current_time_str

                    # Log details of what's being exported without redundant deduplication
                    for i, tweet in enumerate(
                        all_responses[:3]
                    ):  # Log first 3 tweets as sample
                        bt.logging.info(
                            f"  Tweet {i+1}/{min(3, len(all_responses))} Sample:\n"
                            f"    ID: {tweet['Tweet']['ID']}\n"
                            f"    Text: {tweet['Tweet'].get('Text', '')[:100]}...\n"
                            f"    URL: {self.format_tweet_url(tweet['Tweet']['ID'])}\n"
                            f"    TimeParsed: {tweet['Tweet']['TimeParsed']}\n"
                        )

                    if len(all_responses) > 3:
                        bt.logging.info(
                            f"  ... and {len(all_responses) - 3} more tweets"
                        )

                    # Export valid batch directly to API
                    await self.validator.export_tweets(
                        all_responses,
                        query.strip().replace('"', ""),
                    )
                    successful_uids.add(uid)
                else:
                    bt.logging.info(
                        f"❌ Not all tweets from {self.format_miner_info(uid)} passed validation, skipping batch"
                    )
                    invalid_tweet_uids.add(uid)
            except Exception as e:
                bt.logging.error(f"Error processing miner {uid}: {e}")
                continue

        # Log detailed summary of all miners
        bt.logging.info("📊 Miner Response Summary:")
        if no_response_uids:
            bt.logging.info(
                f"  No Response ({len(no_response_uids)}): {sorted(no_response_uids)}"
            )
        if empty_response_uids:
            bt.logging.info(
                f"  Empty Response ({len(empty_response_uids)}): {sorted(empty_response_uids)}"
            )
        if invalid_tweet_uids:
            bt.logging.info(
                f"  Invalid Tweets ({len(invalid_tweet_uids)}): {sorted(invalid_tweet_uids)}"
            )
        if successful_uids:
            bt.logging.info(
                f"  Successful ({len(successful_uids)}): {sorted(successful_uids)}"
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

    # Helper function to format miner info
    def format_miner_info(self, uid: int) -> str:
        """Format miner info with TaoStats link using hotkey."""
        try:
            hotkey = self.validator.metagraph.hotkeys[uid]
            return f"Miner {uid} (https://taostats.io/hotkey/{hotkey})"
        except (IndexError, AttributeError):
            # Fallback if we can't get the hotkey for some reason
            return f"Miner {uid}"
