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

import typing
import bittensor as bt

class SimpleGETProtocol(bt.Synapse):
    """
    A protocol for handling simple GET requests.
    This protocol uses bt.Synapse as its base.

    Attributes:
    - request_url: A string representing the GET request URL.
    - response_data: An optional dictionary which, when filled, represents the GET request's response.
    """

    request_url: str
    response_data: typing.Optional[dict] = None

    def deserialize(self) -> dict:
        """
        Deserialize the GET request's response. This method retrieves the response from
        the miner in the form of response_data, deserializes it (if necessary), and returns it
        as the output of the dendrite.query() call.

        Returns:
        - dict: The deserialized response, which in this case is the value of response_data.

        Example:
        Assuming a SimpleGETProtocol instance has a response_data value of {"profile": {"name": "John", "age": 30}}:
        >>> get_request_instance = SimpleGETProtocol(request_url='http://localhost:8080/api/v1/data/twitter/profile/brendanplayford')
        >>> get_request_instance.response_data = {"profile": {"name": "John", "age": 30}}
        >>> get_request_instance.deserialize()
        {"profile": {"name": "John", "age": 30}}
        """
        return self.response_data
