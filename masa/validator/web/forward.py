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
from masa.miner.web.scraper import WebScraperQuery
from masa.validator.forwarder import Forwarder
from masa.validator.web.reward import get_rewards
from masa.validator.web.parser import web_scraper_parser
from masa.miner.web.scraper import WebScraperRequest


class WebScraperForwarder(Forwarder):

    def __init__(self, validator):
        super(WebScraperForwarder, self).__init__(validator)

    async def forward_query(self, web_scraper_query: WebScraperQuery):
        try:
            def source_method(query):
                return WebScraperRequest().scrape_web(web_scraper_query)

            return await self.forward(
                request=Request(
                    url=web_scraper_query.url,
                    depth=web_scraper_query.depth,
                    type=RequestType.WEB_SCRAPER.value,
                ),
                parser_method=web_scraper_parser,
                source_method=source_method)

        except Exception as e:
            bt.logging.error(
                f"Error during the handle responses process: {str(e)}", exc_info=True
            )
            return []
