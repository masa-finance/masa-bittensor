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


class Forwarder:
    def __init__(self, validator):
        self.validator = validator

    async def forward_request(
        self,
        request: Any,
        sample_size: int = None,
        timeout: int = 30,
        sequential: bool = False,
    ) -> Tuple[List[dict], List[int]]:
        """
        Forward a request to multiple miners.

        Args:
            request: The request to forward
            sample_size: Number of miners to query (if None, uses get_uncalled_miner_uids)
            timeout: Timeout in seconds for each request
            sequential: Whether to query miners sequentially
        """
        try:
            async with self.validator.lock:
                # Create a new dendrite instance for this request
                dendrite = bt.dendrite(wallet=self.validator.wallet)
                try:
                    responses = []
                    successful_uids = []

                    # Get miner UIDs based on sample size
                    if sample_size:
                        miner_uids = await get_random_miner_uids(
                            self.validator, sample_size
                        )
                    else:
                        miner_uids = await get_uncalled_miner_uids(
                            self.validator, 10
                        )  # Default to 10 if not specified

                    if miner_uids is None:
                        bt.logging.warning("No valid miner UIDs found")
                        return [], []

                    # Query miners either sequentially or concurrently
                    if sequential:
                        for uid in miner_uids:
                            try:
                                response = await dendrite(
                                    self.validator.metagraph.axons[uid],
                                    request,
                                    deserialize=True,
                                    timeout=timeout,
                                )
                                if response is not None and isinstance(response, dict):
                                    responses.append(response)
                                    successful_uids.append(uid)
                            except Exception as e:
                                bt.logging.debug(
                                    f"Error querying miner {uid}: {str(e)}"
                                )
                            await asyncio.sleep(
                                1
                            )  # Small delay between sequential requests
                    else:

                        async def query_miner(uid):
                            try:
                                response = await dendrite(
                                    self.validator.metagraph.axons[uid],
                                    request,
                                    deserialize=True,
                                    timeout=timeout,
                                )
                                if response is not None and isinstance(response, dict):
                                    responses.append(response)
                                    successful_uids.append(uid)
                            except Exception as e:
                                bt.logging.debug(
                                    f"Error querying miner {uid}: {str(e)}"
                                )

                        await asyncio.gather(
                            *(query_miner(uid) for uid in miner_uids),
                            return_exceptions=True,
                        )

                    return responses, successful_uids
                finally:
                    # Always close the dendrite session
                    if dendrite:
                        await dendrite.close_session()

        except Exception as e:
            bt.logging.error(f"Error in forward_request: {str(e)}")
            return [], []

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
        """Get volumes from miners."""
        try:
            # Create the request message
            request = {"type": "get_volume"}

            # Forward request to miners
            responses, successful_uids = await self.forward_request(
                request=request,
                sample_size=10,  # Query 10 miners at a time
                timeout=30,
                sequential=False,
            )

            # Process responses
            for response, uid in zip(responses, successful_uids):
                if response and "volume" in response:
                    volume = response["volume"]
                    if isinstance(volume, (int, float)) and volume >= 0:
                        self.validator.scorer.add_volume(str(uid), volume)
                    else:
                        bt.logging.warning(f"Invalid volume from miner {uid}: {volume}")

            self.validator.save_state()
        except Exception as e:
            bt.logging.error(f"Error in get_miners_volumes: {str(e)}")
            bt.logging.debug("Full error details:", exc_info=True)

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
