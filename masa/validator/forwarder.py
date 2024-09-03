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

from masa.utils.uids import get_random_miner_uids
from typing import Any
import bittensor as bt

from masa.miner.twitter.tweets import RecentTweetsSynapse
from masa.miner.twitter.profile import TwitterProfileSynapse
from masa.miner.twitter.followers import TwitterFollowersSynapse
from masa.base.healthcheck import PingMiner, get_external_ip


from datetime import datetime
import random


TIMEOUT = 8


class Forwarder:
    def __init__(self, validator):
        self.validator = validator

    async def send_dendrite_request(
        self, request: Any, sample_size: int, timeout: int = TIMEOUT
    ):
        miner_uids = await get_random_miner_uids(self.validator, k=sample_size)
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
        formatted_responses, _ = await self.send_dendrite_request(
            request=request, sample_size=self.validator.config.neuron.sample_size
        )
        return formatted_responses

    async def get_twitter_followers(self, username: str = "getmasafi", count: int = 10):
        request = TwitterFollowersSynapse(username=username, count=count)
        formatted_responses, _ = await self.send_dendrite_request(
            request, sample_size=self.validator.config.neuron.sample_size
        )
        return formatted_responses

    async def get_recent_tweets(
        self,
        query: str = f"(Bitcoin) since:{datetime.now().strftime('%Y-%m-%d')}",
        count: int = 1,
    ):
        request = RecentTweetsSynapse(query=query, count=count)
        formatted_responses, _ = await self.send_dendrite_request(
            request, sample_size=self.validator.config.neuron.sample_size
        )
        return formatted_responses

    async def get_miners_versions(self):
        versions = await self.validator.get_miner_versions()
        if versions:
            return versions
        return []

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

    async def get_miner_versions(self):
        dendrite = bt.dendrite(wallet=self.validator.wallet)
        request = PingMiner(sent_from=get_external_ip(), is_active=False, version=0)
        all_responses = []
        sample_size = self.validator.config.neuron.sample_size_version
        for i in range(0, len(self.validator.metagraph.axons), sample_size):
            batch = self.validator.metagraph.axons[i : i + sample_size]
            batch_responses = await dendrite(
                batch,
                request,
                deserialize=False,
                timeout=8,
            )
            all_responses.extend(batch_responses)
        self.validator.versions = [response.version for response in all_responses]
        bt.logging.info(f"Miner Versions: {self.versions}")
        self.validator.last_version_check_block = self.validator.block
        return self.validator.versions

    async def get_miner_volumes(self):
        with open("scrape_twitter_keywords.txt", "r") as file:
            keywords_data = file.read()

        keywords_list = keywords_data.split(",")
        random_keyword = random.choice(keywords_list)
        query = (
            f"({random_keyword.strip()}) since:{datetime.now().strftime('%Y-%m-%d')}"
        )
        request = RecentTweetsSynapse(query=query, count=2)
        responses, miner_uids = await self.send_dendrite_request(
            request, sample_size=self.validator.config.neuron.sample_size_volume
        )

        for response, uid in zip(responses, miner_uids):
            # TODO only count tweets / responses that meet a certain sameness threshold!
            if response:
                volume = len(response)
            else:
                volume = 0
            self.validator.scorer.add_volume(int(uid), volume)

        bt.logging.info(f"Responses: {responses}")
