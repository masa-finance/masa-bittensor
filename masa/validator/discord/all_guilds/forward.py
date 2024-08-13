# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

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
from masa.api.request import Request, RequestType
from masa.validator.forwarder import Forwarder
from masa.validator.discord.all_guilds.parser import all_guilds_parser
from masa.miner.masa_protocol_request import REQUEST_TIMEOUT_IN_SECONDS
from masa.miner.discord.all_guilds import DiscordAllGuildsRequest


class DiscordAllGuildsForwarder(Forwarder):

    def __init__(self, validator):
        super(DiscordAllGuildsForwarder, self).__init__(validator)

    async def forward_query(self, limit):
        try:

            def source_method(query):
                return DiscordAllGuildsRequest().get_discord_all_guilds()

            return await self.forward(
                request=Request(type=RequestType.DISCORD_ALL_GUILDS.value),
                parser_method=all_guilds_parser,
                timeout=REQUEST_TIMEOUT_IN_SECONDS,
                source_method=source_method,
                limit=limit,
            )

        except Exception as e:
            bt.logging.error(
                f"Error during the handle responses process: {str(e)}", exc_info=True
            )
            return []
