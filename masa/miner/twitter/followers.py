import bittensor as bt
from typing import List, Optional, Any
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import TwitterFollowerObject

# TODO we can refactor this to synapses directory, as both vali and miner use


class TwitterFollowersSynapse(bt.Synapse):
    username: str
    count: int
    response: Optional[Any] = None

    def deserialize(self) -> Any:
        return self.response


def forward_twitter_followers(
    synapse: TwitterFollowersSynapse,
) -> TwitterFollowersSynapse:
    synapse.response = TwitterFollowersRequest().get_followers(synapse)
    return synapse


class TwitterFollowersRequest(MasaProtocolRequest):
    def __init__(self):
        super().__init__()

    def get_followers(
        self, synapse: TwitterFollowersSynapse
    ) -> List[TwitterFollowerObject]:
        bt.logging.info(
            f"Getting {synapse.count} twitter followers for: {synapse.username}"
        )
        response = self.get(
            f"/data/twitter/followers/{synapse.username}?limit={synapse.count}"
        )
        if response.ok:
            data = self.format(response)
            return data
        else:
            bt.logging.error(
                f"Twitter followers request failed with status code: {response.status_code}"
            )
            return None
