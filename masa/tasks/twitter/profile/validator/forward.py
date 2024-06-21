import bittensor as bt

from masa.validator.forwarder import Forwarder
from masa.tasks.twitter.profile.validator.reward import get_rewards
from masa.tasks.twitter.profile.protocol import TwitterProfileProtocol
from masa.types.twitter import TwitterProfileObject

class TwitterProfileForwarder(Forwarder):

    def __init__(self, validator):
        super(TwitterProfileForwarder, self).__init__(validator)


    async def forward_query(self, query):
        try:
            return await self.forward(request=TwitterProfileProtocol(query=query), get_rewards=get_rewards, parser_object=TwitterProfileObject)

        except Exception as e:
            bt.logging.error(f"Error during the handle responses process: {str(e)}", exc_info=True)
            return []