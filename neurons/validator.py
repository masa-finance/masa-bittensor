# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import bittensor as bt
import time
import random
from typing import Optional

# Bittensor Validator Template:
from masa.base.validator import BaseValidatorNeuron
from masa.api.validator_api import ValidatorAPI
from sentence_transformers import SentenceTransformer
from masa.validator.twitter.tweets.forward import TwitterTweetsForwarder
from masa.miner.twitter.tweets import RecentTweetsQuery

from masa.validator.scorer import Scorer
import aiohttp


class Validator(BaseValidatorNeuron):
    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)
        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )  # Load a pre-trained model for embeddings
        self.scorer = Scorer(self)
        self.API = ValidatorAPI(self)
        bt.logging.info("Validator initialized with config: {}".format(config))

    # note, this function is called
    async def forward(self):
        pass

    async def test_miner_volume(self):
        keywords_url = self.config.validator.twitter_keywords_url
        await self.get_tweets_from_keywords(keywords_url)

    async def fetch_keywords_from_github(self, url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    text_data = await response.text()
                    return {"keywords": text_data}
                else:
                    bt.logging.error(
                        f"Failed to fetch keywords from GitHub: {response.status}"
                    )
                    return None

    async def get_tweets_from_keywords(
        self, github_url: str, limit: Optional[str] = None
    ):
        keywords_data = await self.fetch_keywords_from_github(github_url)

        if not keywords_data:
            return []

        keywords = keywords_data.get("keywords", "")
        if not keywords:
            bt.logging.error("No keywords found in the fetched data.")
            return []

        keywords_list = keywords.split(",")
        all_responses = []

        random_keyword = random.choice(keywords_list)
        query = f"({random_keyword.strip()}) since:2024-08-27"

        bt.logging.info(f"Fetching {query} from miner")
        responses = await TwitterTweetsForwarder(self).forward_query(
            tweet_query=RecentTweetsQuery(query=query, count=3), limit=limit
        )
        all_responses.extend(responses)

        bt.logging.info(f"Responses for {query}: {responses}")
        return all_responses


if __name__ == "__main__":
    with Validator() as validator:
        while True:
            time.sleep(5)
