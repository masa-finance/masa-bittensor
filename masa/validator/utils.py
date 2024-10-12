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


U16_MAX = 65535


# The community uses / bittensor does not
def process_weights_for_netuid(
    uids: Union[NDArray[np.int64], "torch.Tensor"],
    weights: Union[NDArray[np.float32], "torch.FloatTensor"],
    netuid: int,
    subtensor,
    metagraph=None,
    exclude_quantile: int = 0,
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
        exclude_quantile (int): Quantile threshold for excluding lower weights. Defaults to ``0``.

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

    # Network configuration parameters from an subtensor.
    # These parameters determine the range of acceptable weights for each neuron.
    quantile = exclude_quantile / U16_MAX
    min_allowed_weights = subtensor.min_allowed_weights(netuid=netuid)

    # Find all non zero weights.
    non_zero_weight_idx = (
        torch.argwhere(weights > 0).squeeze(dim=1)
        if use_torch()
        else np.argwhere(weights > 0).squeeze(axis=1)
    )
    non_zero_weight_uids = uids[non_zero_weight_idx]
    non_zero_weights = weights[non_zero_weight_idx]
    nzw_size = non_zero_weights.numel() if use_torch() else non_zero_weights.size

    if nzw_size == 0 or metagraph.n < min_allowed_weights:
        bt.logging.warning("No non-zero weights returning all ones.")
        final_weights = (
            torch.ones((metagraph.n)).to(metagraph.n) / metagraph.n
            if use_torch()
            else np.ones((metagraph.n), dtype=np.int64) / metagraph.n
        )
        final_weights_count = (
            torch.tensor(list(range(len(final_weights))))
            if use_torch()
            else np.arange(len(final_weights))
        )
        return (
            (final_weights_count, final_weights)
            if use_torch()
            else (final_weights_count, final_weights)
        )

    elif nzw_size < min_allowed_weights:
        bt.logging.warning(
            "No non-zero weights less then min allowed weight, returning all ones."
        )
        # ( const ): Should this be np.zeros( ( metagraph.n ) ) to reset everyone to build up weight?
        weights = (
            torch.ones((metagraph.n)).to(metagraph.n) * 1e-5
            if use_torch()
            else np.ones((metagraph.n), dtype=np.int64) * 1e-5
        )  # creating minimum even non-zero weights
        weights[non_zero_weight_idx] += non_zero_weights
        nw_arange = (
            torch.tensor(list(range(len(weights))))
            if use_torch()
            else np.arange(len(weights))
        )
        return nw_arange, non_zero_weights

    # Compute the exclude quantile and find the weights in the lowest quantile
    max_exclude = max(0, len(non_zero_weights) - min_allowed_weights) / len(
        non_zero_weights
    )

    exclude_quantile = min([quantile, max_exclude])
    lowest_quantile = (
        non_zero_weights.quantile(exclude_quantile)
        if use_torch()
        else np.quantile(non_zero_weights, exclude_quantile)
    )

    # Exclude all weights below the allowed quantile.
    non_zero_weight_uids = non_zero_weight_uids[lowest_quantile <= non_zero_weights]
    non_zero_weights = non_zero_weights[lowest_quantile <= non_zero_weights]

    return non_zero_weight_uids, non_zero_weights
