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
import asyncio

# Bittensor Validator Template:
from masa.base.validator import BaseValidatorNeuron
from masa.api.server import API


class Validator(BaseValidatorNeuron):
    async def __init__(self, config=None):
        # Initialize parent class first
        await super().__init__(config=config)

        # Initialize API if enabled
        if (
            hasattr(self.config, "enable_validator_api")
            and self.config.enable_validator_api
        ):
            self.API = API(self)
            bt.logging.info("Validator API initialized.")
        bt.logging.info("Validator initialized with config: {}".format(config))


async def main():
    validator = Validator()
    await validator.__init__()  # Explicitly initialize

    async with validator:  # Use async context manager
        while True:
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
