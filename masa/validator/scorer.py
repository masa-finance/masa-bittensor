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
import torch
import scipy.stats as stats
from fastapi.responses import JSONResponse


class Scorer:
    def __init__(self, validator):
        self.validator = validator

    def add_volume(self, miner_uid, volume):
        current_block = self.validator.subtensor.block  # Get the current block number
        tempo = (
            current_block // self.validator.tempo
        )  # Group blocks by tempo, or roughly 72 minutes

        if not self.validator.volumes or self.validator.volumes[-1]["tempo"] != tempo:
            self.validator.volumes.append({"tempo": tempo, "miners": {}})
            self.validator.volumes = self.validator.volumes[
                -self.validator.volume_window :
            ]

        if miner_uid not in self.validator.volumes[-1]["miners"]:
            self.validator.volumes[-1]["miners"][miner_uid] = 0
        self.validator.volumes[-1]["miners"][miner_uid] += volume

    async def score_miner_volumes(self):
        volumes = self.validator.volumes

        miner_volumes = {}
        for volume in volumes[-self.validator.volume_window :]:
            for miner_uid, vol in volume["miners"].items():
                if miner_uid not in miner_volumes:
                    miner_volumes[miner_uid] = 0
                miner_volumes[miner_uid] += vol

        valid_miner_uids = list(miner_volumes.keys())

        if not miner_volumes:
            self.validator.save_state()
            return JSONResponse(content=[])

        mean_volume = sum(miner_volumes.values()) / len(miner_volumes)
        std_dev_volume = (
            sum((x - mean_volume) ** 2 for x in miner_volumes.values())
            / len(miner_volumes)
        ) ** 0.5

        if len(miner_volumes) == 1:
            rewards = [1]
        else:
            rewards = [
                self.kurtosis_based_score(
                    miner_volumes[uid], mean_volume, std_dev_volume
                )
                for uid in valid_miner_uids
            ]
        scores = torch.FloatTensor(rewards).to(self.validator.device)

        self.validator.update_scores(scores, valid_miner_uids)
        if self.validator.should_set_weights():
            try:
                self.validator.set_weights()
            except Exception as e:
                bt.logging.error(f"Failed to set weights: {e}")

        self.validator.last_scoring_block = self.validator.subtensor.block
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

    def calculate_similarity_percentage(self, response_embedding, source_embedding):
        cosine_similarity = torch.nn.functional.cosine_similarity(
            torch.tensor(response_embedding).unsqueeze(0),
            torch.tensor(source_embedding).unsqueeze(0),
        ).item()
        similarity_percentage = (cosine_similarity + 1) / 2 * 100
        return similarity_percentage

    def kurtosis_based_score(self, volume, mean, std_dev, scale_factor=1.0):
        if std_dev == 0:
            return 0
        z_score = (volume - mean) / std_dev
        return stats.norm.cdf(z_score) * scale_factor
