# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Opentensor Foundation

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

import pytest
from neurons.miner import Miner
from masa.base.miner import BaseMinerNeuron

from masa.synapses import (
    TwitterProfileSynapse,
    TwitterFollowersSynapse,
    RecentTweetsSynapse,
)

from masa.miner.twitter.profile import (
    TwitterProfileSynapse,
)
from masa.miner.twitter.followers import (
    TwitterFollowersRequest,
)
from masa.miner.twitter.tweets import TwitterTweetsRequest


class TestMiner:

    @pytest.fixture
    async def miner(self):
        config = BaseMinerNeuron.config()
        config.netuid = 165
        config.subtensor.network = "wss://test.finney.opentensor.ai:443"
        config.wallet.name = "miner"
        config.wallet.hotkey = "default"
        config.blacklist.force_validator_permit = True
        config.axon.port = 8091

        miner_instance = Miner(config=config)
        return miner_instance

    @pytest.mark.asyncio
    async def test_miner_has_uid(self, miner):
        miner_instance = await miner
        uid = miner_instance.uid
        assert uid > -1, "UID should be greater than -1 for success"

    # TODO CI/CD yet to support the protocol node
    # def test_miner_protocol_profile_request(self):
    #     synapse = TwitterProfileSynapse(username="getmasafi")
    #     profile = TwitterProfileRequest().get_profile(synapse=synapse)
    #     assert profile is not None, "profile should not be None"

    # TODO CI/CD yet to support the protocol node
    # def test_miner_protocol_followers_request(self):
    #     synapse = TwitterFollowersSynapse(username="getmasafi", count=3)
    #     followers = TwitterFollowersRequest().get_followers(synapse=synapse)
    #     assert followers is not None, "followers should not be None"
    #     assert len(followers) > 0, "followers should exist"

    # TODO CI/CD yet to support the protocol node
    # def test_miner_protocol_tweets_request(self):
    #     synapse = RecentTweetsSynapse(query="btc", count=3)
    #     tweets = TwitterTweetsRequest(10).get_recent_tweets(synapse=synapse)
    #     assert tweets is not None, "tweets should not be None"
    #     assert len(tweets) > 0, "tweets should exist"
