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
        try:
            volumes = self.validator.volumes
            bt.logging.debug(f"Processing volumes: {volumes}")

            if not volumes:
                bt.logging.info("No volumes to score yet")
                return JSONResponse(content=[])

            miner_volumes = {}
            for volume in volumes[-self.validator.volume_window :]:
                bt.logging.debug(f"Processing volume entry: {volume}")
                miners_dict = volume.get("miners", {})
                bt.logging.debug(f"Miners dict: {miners_dict}")
                for miner_uid, vol in miners_dict.items():
                    try:
                        uid = int(miner_uid)
                        if uid not in miner_volumes:
                            miner_volumes[uid] = 0
                        miner_volumes[uid] += float(vol)
                    except (ValueError, TypeError) as e:
                        bt.logging.warning(
                            f"Invalid miner_uid {miner_uid} or volume {vol}: {e}"
                        )
                        continue

            valid_miner_uids = list(miner_volumes.keys())
            bt.logging.debug(f"Valid miner UIDs: {valid_miner_uids}")
            bt.logging.debug(f"Miner volumes: {miner_volumes}")

            if not miner_volumes:
                bt.logging.warning("No valid miner volumes found")
                self.validator.save_state()
                return JSONResponse(content=[])

            mean_volume = sum(miner_volumes.values()) / len(miner_volumes)
            bt.logging.debug(f"Mean volume: {mean_volume}")

            squared_diffs = [(x - mean_volume) ** 2 for x in miner_volumes.values()]
            bt.logging.debug(f"Squared differences: {squared_diffs}")

            variance = sum(squared_diffs) / len(miner_volumes)
            bt.logging.debug(f"Variance: {variance}")

            std_dev_volume = max(variance**0.5, 1e-8)
            bt.logging.debug(f"Standard deviation: {std_dev_volume}")

            if len(miner_volumes) == 1:
                rewards = [1]
                bt.logging.debug("Single miner case - setting reward to 1")
            else:
                rewards = []
                for uid in valid_miner_uids:
                    try:
                        volume = miner_volumes[uid]
                        bt.logging.debug(
                            f"Calculating score for UID {uid} with volume {volume}"
                        )
                        score = self.kurtosis_based_score(
                            volume, mean_volume, std_dev_volume
                        )
                        bt.logging.debug(f"Score for UID {uid}: {score}")
                        rewards.append(float(score))
                    except Exception as e:
                        bt.logging.error(f"Error calculating score for uid {uid}: {e}")
                        rewards.append(0.0)

            scores = torch.FloatTensor(rewards).to(self.validator.device)
            bt.logging.debug(f"Final scores tensor: {scores}")

            async with self.validator.lock:
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
                        "uid": int(uid),
                        "volume": float(miner_volumes[uid]),
                        "score": float(rewards[i]),
                    }
                    for i, uid in enumerate(valid_miner_uids)
                ]
                return JSONResponse(content=serializable_volumes)
            return JSONResponse(content=[])
        except Exception as e:
            bt.logging.error(f"Error in score_miner_volumes: {str(e)}")
            bt.logging.error(f"Full error details:", exc_info=True)
            return JSONResponse(content=[])

    def calculate_similarity_percentage(self, response_embedding, source_embedding):
        cosine_similarity = torch.nn.functional.cosine_similarity(
            torch.tensor(response_embedding).unsqueeze(0),
            torch.tensor(source_embedding).unsqueeze(0),
        ).item()
        similarity_percentage = (cosine_similarity + 1) / 2 * 100
        return similarity_percentage

    def kurtosis_based_score(self, volume, mean, std_dev, scale_factor=1.0):
        try:
            if std_dev < 1e-8:  # Numerical stability
                return 0.0
            z_score = (float(volume) - float(mean)) / float(std_dev)
            return float(stats.norm.cdf(z_score) * scale_factor)
        except Exception as e:
            bt.logging.error(f"Error in kurtosis_based_score: {e}")
            return 0.0
