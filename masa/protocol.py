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

class JSONProtocol(bt.Synapse):
    """
    A protocol for handling unstructured JSON blobs and converting them into structured JSON.
    This protocol uses bt.Synapse as its base.

    Attributes:
    - unstructured_json: A string representing the unstructured JSON input.
    - structured_json: An optional dictionary which, when filled, represents the structured JSON output.
    """

    # Required request input, filled by sending dendrite caller.
    unstructured_json: str

    # Optional request output, filled by receiving axon.
    structured_json: typing.Optional[dict] = None

    def deserialize(self) -> dict:
        """
        Deserialize the structured JSON output. This method retrieves the response from
        the miner in the form of structured_json, deserializes it and returns it
        as the output of the dendrite.query() call.

        Returns:
        - dict: The deserialized response, which in this case is the value of structured_json.

        Example:
        Assuming a JSONProtocol instance has a structured_json value of {"name": "John", "age": 30}:
        >>> json_instance = JSONProtocol(unstructured_json='{"name": "John", "age": "30 years"}')
        >>> json_instance.structured_json = {"name": "John", "age": 30}
        >>> json_instance.deserialize()
        {"name": "John", "age": 30}
        """
        return self.structured_json
