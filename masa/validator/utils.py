# The MIT License (MIT)
# Copyright © 2024 Opentensor Foundation
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

"""Conversion for weight between chain representation and np.array or torch.Tensor"""

from typing import Union
import numpy as np

from numpy.typing import NDArray

import bittensor as bt
from bittensor.utils.registration import torch, use_torch


def process_weights_for_netuid(
    uids: Union[NDArray[np.int64], "torch.Tensor"],
    weights: Union[NDArray[np.float32], "torch.FloatTensor"],
    netuid: int,
    subtensor,
    metagraph=None,
) -> Union[
    tuple["torch.Tensor", "torch.FloatTensor"],
    tuple[NDArray[np.int64], NDArray[np.float32]],
]:
    """
    Processes weight tensors for a given subnet id using the provided weight and UID arrays, applying constraints and normalization based on the subtensor and metagraph data. This function can handle both NumPy arrays and PyTorch tensors.

    Args:
        uids (Union[NDArray[np.int64], "torch.Tensor"]): Array of unique identifiers of the neurons.
        weights (Union[NDArray[np.float32], "torch.Tensor"]): Array of weights associated with the user IDs.
        netuid (int): The network uid to process weights for.
        subtensor (Subtensor): Subtensor instance to access blockchain data.
        metagraph (Optional[Metagraph]): Metagraph instance for additional network data. If None, it is fetched from the subtensor using the netuid.

    Returns:
        Union[tuple["torch.Tensor", "torch.FloatTensor"], tuple[NDArray[np.int64], NDArray[np.float32]]]: tuple containing the array of user IDs and the corresponding normalized weights. The data type of the return matches the type of the input weights (NumPy or PyTorch).
    """

    # Get latest metagraph from chain if metagraph is None.
    if metagraph is None:
        metagraph = subtensor.metagraph(netuid)

    # Cast weights to floats.
    if use_torch():
        if not isinstance(weights, torch.FloatTensor):
            weights = weights.type(torch.float32)
    else:
        if not isinstance(weights, np.float32):
            weights = weights.astype(np.float32)

    # Find all non zero weights.
    non_zero_weight_idx = (
        torch.argwhere(weights > 0).squeeze(dim=1)
        if use_torch()
        else np.argwhere(weights > 0).squeeze(axis=1)
    )
    non_zero_weight_uids = uids[non_zero_weight_idx]
    non_zero_weights = weights[non_zero_weight_idx]

    return non_zero_weight_uids, non_zero_weights
