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
from typing import Any
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

        if len(miner_uids) == 0:
            return [], []

        dendrite = bt.dendrite(wallet=self.validator.wallet)
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

    async def ping_axons(self):
        request = PingAxonSynapse(
            sent_from=get_external_ip(), is_active=False, version=0
        )
        sample_size = self.validator.subnet_config.get("healthcheck").get("sample_size")
        dendrite = bt.dendrite(wallet=self.validator.wallet)
        all_responses = []
        for i in range(0, len(self.validator.metagraph.axons), sample_size):
            batch = self.validator.metagraph.axons[i : i + sample_size]
            batch_responses = await dendrite(
                batch,
                request,
                deserialize=False,
                timeout=self.validator.subnet_config.get("healthcheck").get("timeout"),
            )
            all_responses.extend(batch_responses)

        self.validator.versions = [response.version for response in all_responses]
        bt.logging.info(f"Miner Versions: {self.validator.versions}")
        self.validator.last_healthcheck_block = self.validator.subtensor.block
        return [
            {
                "status_code": response.dendrite.status_code,
                "status_message": response.dendrite.status_message,
                "version": response.version,
                "uid": all_responses.index(response),
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

    async def get_miners_volumes(self):
        if len(self.validator.versions) == 0:
            bt.logging.info("Pinging axons to get miner versions...")
            return await self.ping_axons()
        if len(self.validator.keywords) == 0 or self.check_tempo():
            await self.fetch_twitter_queries()
        if len(self.validator.subnet_config) == 0 or self.check_tempo():
            await self.fetch_subnet_config()

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
        for response, uid in zip(responses, miner_uids):
            valid_tweets = []
            all_responses = dict(response).get("response", [])
            if not all_responses:
                continue

            # Use regex to remove all leading zeros, whitespace, or similar characters
            unique_tweets_response = list(
                {
                    re.sub(r"^[0೦०\s]+", "", resp["Tweet"]["ID"]).strip(): {
                        **resp,
                        "Tweet": {
                            **resp["Tweet"],
                            "ID": re.sub(r"^[0೦०\s]+", "", resp["Tweet"]["ID"]).strip(),
                        },
                    }
                    for resp in all_responses
                    if "Tweet" in resp and "ID" in resp["Tweet"]
                }.values()
            )

            if unique_tweets_response is not None:
                # note, first spot check this payload, ensuring a random tweet is valid
                random_tweet = dict(random.choice(unique_tweets_response)).get(
                    "Tweet", {}
                )

                is_valid = TweetValidator().validate_tweet(
                    random_tweet.get("ID"),
                    random_tweet.get("Name"),
                    random_tweet.get("Username"),
                    random_tweet.get("Text"),
                    random_tweet.get("Timestamp"),
                    random_tweet.get("Hashtags"),
                )

                await asyncio.sleep(1)

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
                    bt.logging.warning(
                        f"Query: {random_keyword} is not in the tweet: {fields_to_check}"
                    )

                tweet_timestamp = datetime.fromtimestamp(
                    random_tweet.get("Timestamp", 0), UTC
                )

                yesterday = datetime.now(UTC).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) - timedelta(days=1)
                is_since_date_requested = yesterday <= tweet_timestamp

                if not is_since_date_requested:
                    bt.logging.warning(
                        f"Tweet timestamp {tweet_timestamp} is not since {yesterday}"
                    )

                # note, they passed the spot check!
                if is_valid and query_in_tweet and is_since_date_requested:
                    bt.logging.success(
                        f"Miner {uid} passed the spot check with query: {random_keyword}"
                    )
                    for tweet in unique_tweets_response:
                        if tweet:
                            valid_tweets.append(tweet)
                else:
                    bt.logging.warning(f"Miner {uid} failed the spot check!")

            all_valid_tweets.extend(valid_tweets)

            # note, score only unique tweets per miner (uid)
            uid_int = int(uid)

            if not self.validator.tweets_by_uid.get(uid_int):
                self.validator.tweets_by_uid[uid_int] = {
                    tweet["Tweet"]["ID"] for tweet in valid_tweets
                }
                self.validator.scorer.add_volume(uid_int, len(valid_tweets))
                bt.logging.success(
                    f"Miner {uid_int} produced {len(valid_tweets)} valid new tweets"
                )
            else:
                existing_tweet_ids = self.validator.tweets_by_uid[uid_int]
                new_tweet_ids = {tweet["Tweet"]["ID"] for tweet in valid_tweets}
                updates = new_tweet_ids - existing_tweet_ids
                self.validator.tweets_by_uid[uid_int].update(new_tweet_ids)
                self.validator.scorer.add_volume(uid_int, len(updates))
                bt.logging.success(
                    f"Miner {uid_int} produced {len(updates)} new tweets, with a total of {len(self.validator.tweets_by_uid[uid_int])}."
                )

        # Send tweets to API
        await self.validator.export_tweets(
            list({tweet["Tweet"]["ID"]: tweet for tweet in all_valid_tweets}.values()),
            query.strip().replace('"', ""),
        )

        # note, set the last volume block to the current block
        self.validator.last_volume_block = self.validator.subtensor.block

    def check_tempo(self) -> bool:
        if self.validator.last_tempo_block == 0:
            self.validator.last_tempo_block = self.validator.subtensor.block
            return True

        tempo = self.validator.tempo
        blocks_since_last_check = (
            self.validator.subtensor.block - self.validator.last_tempo_block
        )
        if blocks_since_last_check >= tempo:
            self.validator.last_tempo_block = self.validator.subtensor.block
            return True
        else:
            return False

    def normalize_whitespace(self, s: str) -> str:
        return " ".join(s.split())
