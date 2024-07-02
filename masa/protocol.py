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

from typing import Optional
import bittensor as bt
from masa.types.twitter import TwitterProfileObject


class TwitterProfileProtocol(bt.Synapse):
    """
    A protocol for handling Twitter profile requests and responses.
    This protocol uses bt.Synapse as its base.

    Attributes:
    - profile_request: A string representing the Twitter profile request.
    - profile_response: An optional dictionary which, when filled, represents the Twitter profile response.
    """

    profile_request: str
    profile_response: Optional[TwitterProfileObject] = None

    def deserialize(self) -> Optional[TwitterProfileObject]:
        """
        Deserialize the Twitter profile response. This method retrieves the response from
        the miner in the form of profile_response, deserializes it and returns it
        as the output of the dendrite.query() call.

        Returns:
        - dict: The deserialized response, which in this case is the value of profile_response.
        """
        return self.profile_response
