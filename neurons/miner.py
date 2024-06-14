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

import time
import typing
import bittensor as bt

# import base miner class which takes care of most of the boilerplate
from masa.base.miner import BaseMinerNeuron
from masa.api.request import Request, RequestType
from masa.miner.discord.profile import DiscordProfileRequest
from masa.miner.twitter.profile import TwitterProfileRequest
from masa.miner.twitter.followers import TwitterFollowersRequest
from masa.miner.twitter.tweets import RecentTweetsQuery, TwitterTweetsRequest
from masa.miner.web.scraper import WebScraperQuery, WebScraperRequest

delay = 0
class Miner(BaseMinerNeuron):
    def __init__(self, config=None):
        super(Miner, self).__init__(config=config)
        bt.logging.info("Miner initialized with config: {}".format(config))


    async def forward(
        self, synapse: Request
    ) -> Request:
        print(f"Sleeping for rate limiting purposes: {delay}s")
        time.sleep(delay)
        
        try:
            request_type = synapse.type
            
            if request_type == RequestType.TWITTER_PROFILE.value:
                profile = TwitterProfileRequest().get_profile(synapse.query)
                if profile != None:
                    profile_dict = dict(profile)
                    synapse.response = profile_dict
                else:
                    bt.logging.error(f"Failed to fetch Twitter profile for {synapse.query}.")
        
            elif request_type == RequestType.TWITTER_FOLLOWERS.value:
                followers = TwitterFollowersRequest().get_followers(synapse.query)
                if followers != None:
                    synapse.response = followers
                else:
                    bt.logging.error(f"Failed to fetch Twitter followers for {synapse.query}.")

            elif request_type == RequestType.TWITTER_TWEETS.value:
                tweets = TwitterTweetsRequest().get_recent_tweets(RecentTweetsQuery(query=synapse.query, count=synapse.count))
                if tweets != None:
                    synapse.response = tweets
                else:
                    bt.logging.error(f"Failed to fetch Twitter tweets for {synapse.query}.")
            
            elif request_type == RequestType.WEB_SCRAPER.value:
                web_scraped_data = WebScraperRequest().scrape_web(WebScraperQuery(url=synapse.url, depth=synapse.depth))
                if web_scraped_data != None:
                    synapse.response = web_scraped_data
                else:
                    bt.logging.error(f"Failed to scrape for {synapse.url}.")

            elif request_type == RequestType.DISCORD_PROFILE.value:
                discord_profile = DiscordProfileRequest().get_profile(synapse.query)
                if discord_profile != None:
                    synapse.response = discord_profile
                else:
                    bt.logging.error(f"Failed to scrape for {synapse.url}.")

        except Exception as e:
            bt.logging.error(f"Exception occurred while doing work for {synapse.query}: {str(e)}", exc_info=True)
            
        return synapse

    async def blacklist(self, synapse: Request) -> typing.Tuple[bool, str]:

        if self.check_tempo(synapse):
            self.check_stake(synapse)

        hotkey = synapse.dendrite.hotkey
        uid = self.metagraph.hotkeys.index(hotkey)

        bt.logging.info(f"Neurons Staked: {self.neurons_permit_stake}")
        bt.logging.info(f"Validator Permit: {self.metagraph.validator_permit[uid]}")

        if not self.config.blacklist.allow_non_registered and hotkey not in self.metagraph.hotkeys:
            bt.logging.warning(f"Blacklisting un-registered hotkey {hotkey}")
            return True, "Unrecognized hotkey"
        if self.config.blacklist.force_validator_permit and not self.metagraph.validator_permit[uid]:
            bt.logging.warning(f"Blacklisting a request from non-validator hotkey {hotkey}")
            return True, "Non-validator hotkey"
        if hotkey not in self.neurons_permit_stake.keys():
            bt.logging.warning(f"Blacklisting a request from neuron without enough staked: {hotkey}")
            return True, "Non-staked neuron"
        
        bt.logging.info(f"Not Blacklisting recognized hotkey {hotkey}")
        return False, "Hotkey recognized!"

    async def priority(self, synapse: Request) -> float:
        caller_uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        priority = float(self.metagraph.S[caller_uid])
        bt.logging.trace(f"Prioritizing {synapse.dendrite.hotkey} with value: ", priority)
        return priority
    
    def check_stake(self, synapse: Request):
        current_stakes = self.metagraph.S
        hotkey = synapse.dendrite.hotkey
        uid = self.metagraph.hotkeys.index(hotkey)
        current_block = self.subtensor.get_current_block()
        
        if current_stakes[uid] < self.min_stake_required:
            if hotkey in self.neurons_permit_stake.keys():
                del self.neurons_permit_stake[hotkey]
                bt.logging.info(f"Removed neuron {hotkey} from staked list due to insufficient stake.")
        else:
            self.neurons_permit_stake[hotkey] = current_block
            bt.logging.info(f"Added neuron {hotkey} to staked list.")

    
    def check_tempo(self, synapse: Request) -> bool:
        hotkey = synapse.dendrite.hotkey
        last_checked_block = self.neurons_permit_stake.get(hotkey)
        if last_checked_block is None:
            bt.logging.info(f"There is no last checked block, starting tempo check...")
            return True
        
        blocks_since_last_check = self.subtensor.get_current_block() - last_checked_block
        if blocks_since_last_check >= self.tempo:
            bt.logging.info(f"A tempo has passed.  Blocks since last check: {blocks_since_last_check}")
            return True
        else:
            bt.logging.info(f"Not yet a tempo since last check. Blocks since last check: {blocks_since_last_check}")
            return False
        


if __name__ == "__main__":
    with Miner() as miner:
        while True:
            print("Miner running...", time.time())
            time.sleep(5)