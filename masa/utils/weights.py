# The MIT License (MIT)
# Copyright © 2024 Opentensor Foundation
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

"""Conversion for weight between chain representation and np.array or torch.Tensor"""

import logging
import typing
from typing import Union, Optional

import numpy as np

from numpy.typing import NDArray

from bittensor.utils.btlogging import logging
from bittensor.utils.registration import legacy_torch_api_compat, torch

if typing.TYPE_CHECKING:
    from bittensor.core.metagraph import Metagraph
    from bittensor.core.subtensor import Subtensor


U16_MAX = 65535


# Uses in `bittensor.utils.weight_utils.process_weights_for_netuid`
@legacy_torch_api_compat
def normalize_max_weight(
    x: Union[NDArray[np.float32], "torch.FloatTensor"], limit: float = 0.1
) -> Union[NDArray[np.float32], "torch.FloatTensor"]:
    """Normalizes the tensor x so that sum(x) = 1 and the max value is not greater than the limit.
    Args:
        x (:obj:`np.float32`): Tensor to be max_value normalized.
        limit: float: Max value after normalization.

    Returns:
        y (:obj:`np.float32`): Normalized x tensor.
    """
    epsilon = 1e-7  # For numerical stability after normalization

    weights = x.copy()
    values = np.sort(weights)

    if x.sum() == 0 or x.shape[0] * limit <= 1:
        return np.ones_like(x) / x.shape[0]
    else:
        estimation = values / values.sum()

        if estimation.max() <= limit:
            return weights / weights.sum()

        # Find the cumulative sum and sorted tensor
        cumsum = np.cumsum(estimation, 0)

        # Determine the index of cutoff
        estimation_sum = np.array(
            [(len(values) - i - 1) * estimation[i] for i in range(len(values))]
        )
        n_values = (estimation / (estimation_sum + cumsum + epsilon) < limit).sum()

        # Determine the cutoff based on the index
        cutoff_scale = (limit * cumsum[n_values - 1] - epsilon) / (
            1 - (limit * (len(estimation) - n_values))
        )
        cutoff = cutoff_scale * values.sum()

        # Applying the cutoff
        weights[weights > cutoff] = cutoff

        y = weights / weights.sum()

        return y


# The community uses / bittensor does not
async def process_weights_for_netuid(
    uids: Union[NDArray[np.int64], "torch.Tensor"],
    weights: Union[NDArray[np.float32], "torch.Tensor"],
    netuid: int,
    subtensor: "Subtensor",
    metagraph: Optional["Metagraph"] = None,
    exclude_quantile: int = 0,
) -> tuple[NDArray[np.int64], NDArray[np.float32]]:
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
        tuple[NDArray[np.int64], NDArray[np.float32]]: tuple containing the array of user IDs and the corresponding normalized weights.
    """

    # Get latest metagraph from chain if metagraph is None.
    if metagraph is None:
        metagraph = await subtensor.metagraph(netuid)

    # Cast weights to NumPy float32 if needed
    if not isinstance(weights, np.ndarray) or weights.dtype != np.float32:
        weights = weights.astype(np.float32)

    # Network configuration parameters from an subtensor.
    # These parameters determine the range of acceptable weights for each neuron.
    quantile = exclude_quantile / U16_MAX
    min_allowed_weights = await subtensor.min_allowed_weights(netuid=netuid)
    max_weight_limit = await subtensor.max_weight_limit(netuid=netuid)
    logging.debug("quantile", quantile)
    logging.debug("min_allowed_weights", min_allowed_weights)
    logging.debug("max_weight_limit", max_weight_limit)

    # Find all non zero weights.
    non_zero_weight_idx = np.argwhere(weights > 0).squeeze(axis=1)
    non_zero_weight_uids = uids[non_zero_weight_idx]
    non_zero_weights = weights[non_zero_weight_idx]
    nzw_size = non_zero_weights.size

    if nzw_size == 0 or metagraph.n < min_allowed_weights:
        logging.warning("No non-zero weights returning all ones.")
        final_weights = np.ones((metagraph.n), dtype=np.float32) / metagraph.n
        final_weights_count = np.arange(len(final_weights))
        return final_weights_count, final_weights

    elif nzw_size < min_allowed_weights:
        logging.warning(
            "No non-zero weights less then min allowed weight, returning all ones."
        )
        weights = np.ones((metagraph.n), dtype=np.float32) * 1e-5
        weights[non_zero_weight_idx] += non_zero_weights
        normalized_weights = normalize_max_weight(x=weights, limit=max_weight_limit)
        nw_arange = np.arange(len(normalized_weights))
        return nw_arange, normalized_weights

    # Compute the exclude quantile and find the weights in the lowest quantile
    max_exclude = max(0, len(non_zero_weights) - min_allowed_weights) / len(
        non_zero_weights
    )
    exclude_quantile = min([quantile, max_exclude])
    lowest_quantile = np.quantile(non_zero_weights, exclude_quantile)

    logging.debug("max_exclude", max_exclude)
    logging.debug("exclude_quantile", exclude_quantile)
    logging.debug("lowest_quantile", lowest_quantile)

    # Exclude all weights below the allowed quantile.
    non_zero_weight_uids = non_zero_weight_uids[lowest_quantile <= non_zero_weights]
    non_zero_weights = non_zero_weights[lowest_quantile <= non_zero_weights]

    # Normalize weights and return.
    normalized_weights = normalize_max_weight(
        x=non_zero_weights, limit=max_weight_limit
    )

    return non_zero_weight_uids, normalized_weights
