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
import bittensor as bt
from masa.api.request import RequestType

# Bittensor Validator Template:
from masa.base.validator import BaseValidatorNeuron
from masa.api.validator_api import ValidatorAPI


class Validator(BaseValidatorNeuron):
    def __init__(self, config=None):
        super(Validator, self).__init__(config=config)
        self.API = ValidatorAPI(self)
        bt.logging.info("Validator initialized with config: {}".format(config))

    async def forward(
        self, request="brendanplayford", type=RequestType.TWITTER_PROFILE.value
    ):
        pass

    def update_weights(self, scores):
        # Example: Update weights (this is a placeholder for actual weight update logic)
        for score in scores:
            # TODO Update logic here
            pass


if __name__ == "__main__":
    with Validator() as validator:
        while True:
            bt.logging.info("Validator running...")
            time.sleep(5)
