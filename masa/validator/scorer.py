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
import torch
from fastapi.responses import JSONResponse
from sklearn.cluster import KMeans


class Scorer:
    def __init__(self, validator):
        self.validator = validator

    def add_volume(self, miner_uid, volume):
        """
        Adds the volume returned by a miner to the block counter, grouped every 360 blocks.

        Args:
            miner_uid (str): The unique identifier of the miner.
            volume (float): The volume to be added.
        """
        current_block = bt.metagraph(
            # TODO ensure this works?
            self.validator.config.netuid,
            self.validator.config.subtensor,
        ).block  # Get the current block number
        block_group = current_block // 360  # Group blocks by 360

        if (
            not self.validator.volumes
            or self.validator.volumes[-1]["block_group"] != block_group
        ):
            # If volumes list is empty or the last entry is not for the current block group, add a new entry
            self.validator.volumes.append({"block_group": block_group, "miners": {}})

        if miner_uid not in self.validator.volumes[-1]["miners"]:
            self.validator.volumes[-1]["miners"][miner_uid] = 0

        self.validator.volumes[-1]["miners"][miner_uid] += volume

    async def score_miner_volumes(self):
        volumes = self.validator.volumes

        # Extract the miner UIDs and their corresponding volumes
        miner_volumes = {}
        for volume in volumes:
            for miner_uid, vol in volume["miners"].items():
                if miner_uid not in miner_volumes:
                    miner_volumes[miner_uid] = 0
                miner_volumes[miner_uid] += vol

        # Get the list of valid miner UIDs
        valid_miner_uids = list(miner_volumes.keys())

        # Normalize the volumes to get rewards
        max_volume = max(miner_volumes.values())
        rewards = [miner_volumes[uid] / max_volume for uid in valid_miner_uids]

        # Update the scores based on the rewards
        scores = torch.FloatTensor(rewards).to(self.validator.device)
        # note this also saves validator state
        self.validator.update_scores(scores, valid_miner_uids)

        if self.validator.should_set_weights():
            try:
                self.validator.set_weights()
            except Exception as e:
                bt.logging.error(f"Failed to set weights: {e}")

        # return the volumes along with their scores!
        if volumes:
            serializable_volumes = [
                {
                    "uid": int(miner_uid),
                    "volume": float(miner_volumes[miner_uid]),
                    "score": rewards[valid_miner_uids.index(miner_uid)],
                }
                for miner_uid in valid_miner_uids
            ]
            return JSONResponse(content=serializable_volumes)
        return JSONResponse(content=[])

    # TODO use this to validate that a tweet is actually a tweet
    def calculate_similarity_percentage(self, response_embedding, source_embedding):
        # Calculate the cosine similarity between the response and the source of truth
        cosine_similarity = torch.nn.functional.cosine_similarity(
            torch.tensor(response_embedding).unsqueeze(0),
            torch.tensor(source_embedding).unsqueeze(0),
        ).item()
        # Convert cosine similarity to percentage
        similarity_percentage = (cosine_similarity + 1) / 2 * 100
        return similarity_percentage
