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
import sys

from masa.base.validator import BaseValidatorNeuron
from masa.api.server import API


class Validator(BaseValidatorNeuron):
    def __init__(self, config=None):
        super().__init__(config=config)
        self._is_initialized = False

    @classmethod
    async def create(cls, config=None):
        if config is None:
            config = cls.config()

        self = cls(config=config)
        await self.initialize(config)
        return self

    async def initialize(self, config=None):
        if self._is_initialized:
            return

        await super().initialize(config)

        if (
            hasattr(self.config, "enable_validator_api")
            and self.config.enable_validator_api
        ):
            self.API = API(self)
            bt.logging.info("Validator API initialized.")

        self._is_initialized = True


async def main():
    validator = await Validator.create()
    bt.logging.info(
        f"🚀 Validator | Network: {validator.config.subtensor.network} | Netuid: {validator.config.netuid}"
    )
    bt.logging.debug(f"Command: {' '.join(sys.argv)}")
    bt.logging.info(f"📂 Path | {validator.config.neuron.full_path}")
    await validator.run()


if __name__ == "__main__":
    asyncio.run(main())
