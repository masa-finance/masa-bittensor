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
import traceback
import sys


class Scorer:
    def __init__(self, validator):
        self.validator = validator

    def add_volume(self, miner_uid, volume, current_block):
        try:
            tempo = (
                current_block // self.validator.tempo
            )  # Group blocks by tempo, or roughly 72 minutes

            if (
                not self.validator.volumes
                or self.validator.volumes[-1]["tempo"] != tempo
            ):
                self.validator.volumes.append({"tempo": tempo, "miners": {}})
                self.validator.volumes = self.validator.volumes[
                    -self.validator.volume_window :
                ]

            # Always store miner_uid as string in volumes
            miner_uid_str = str(miner_uid)
            if miner_uid_str not in self.validator.volumes[-1]["miners"]:
                self.validator.volumes[-1]["miners"][miner_uid_str] = 0
            self.validator.volumes[-1]["miners"][miner_uid_str] += volume
        except Exception:
            bt.logging.error(f"Exception in add_volume:\n{traceback.format_exc()}")
            raise

    async def score_miner_volumes(self, current_block: int):
        try:
            bt.logging.debug("Starting score_miner_volumes...")
            volumes = self.validator.volumes

            if not volumes:
                bt.logging.info("No volumes to score")
                return JSONResponse(content=[])

            window_size = min(self.validator.volume_window, len(volumes))
            miner_volumes = {}

            # Process volumes and aggregate miner data
            try:
                for volume in volumes[-window_size:]:
                    bt.logging.debug(f"Processing volume from tempo {volume['tempo']}")
                    for miner_uid_str, vol in volume["miners"].items():
                        # Ensure consistent string keys
                        miner_uid_str = str(miner_uid_str)
                        if miner_uid_str not in miner_volumes:
                            miner_volumes[miner_uid_str] = 0
                        miner_volumes[miner_uid_str] += vol
            except Exception:
                bt.logging.error(
                    f"Exception processing volumes:\n{traceback.format_exc()}"
                )
                return JSONResponse(content=[])

            bt.logging.debug(f"Aggregated miner volumes: {miner_volumes}")

            try:
                # Convert string UIDs to integers for scoring
                valid_miner_uids = []
                for uid_str in miner_volumes.keys():
                    try:
                        uid_int = int(uid_str)
                        if uid_int < len(
                            self.validator.scores
                        ):  # Ensure UID is in valid range
                            valid_miner_uids.append(uid_int)
                        else:
                            bt.logging.warning(
                                f"UID {uid_int} is out of range, skipping"
                            )
                    except ValueError:
                        bt.logging.warning(f"Invalid UID format: {uid_str}, skipping")

                bt.logging.debug(f"Valid miner UIDs for scoring: {valid_miner_uids}")
            except Exception:
                bt.logging.error(
                    f"Exception validating UIDs:\n{traceback.format_exc()}"
                )
                return JSONResponse(content=[])

            if not valid_miner_uids:
                bt.logging.warning("No valid miner UIDs to score")
                return JSONResponse(content=[])

            try:
                mean_volume = sum(miner_volumes.values()) / len(miner_volumes)
                std_dev_volume = (
                    sum((x - mean_volume) ** 2 for x in miner_volumes.values())
                    / len(miner_volumes)
                ) ** 0.5
                bt.logging.debug(
                    f"Volume statistics - Mean: {mean_volume:.2f}, StdDev: {std_dev_volume:.2f}"
                )
            except Exception:
                bt.logging.error(
                    f"Exception calculating statistics:\n{traceback.format_exc()}"
                )
                return JSONResponse(content=[])

            try:
                if len(valid_miner_uids) == 1:
                    rewards = [1]
                else:
                    rewards = []
                    for uid in valid_miner_uids:
                        volume = miner_volumes[
                            str(uid)
                        ]  # Convert UID to string for lookup
                        reward = self.kurtosis_based_score(
                            volume, mean_volume, std_dev_volume
                        )
                        rewards.append(reward)
                        bt.logging.debug(
                            f"UID {uid}: volume={volume}, reward={reward:.4f}"
                        )

                scores = torch.FloatTensor(rewards).to(self.validator.device)
            except Exception:
                bt.logging.error(
                    f"Exception calculating rewards:\n{traceback.format_exc()}"
                )
                return JSONResponse(content=[])

            try:
                bt.logging.debug("Calling update_scores...")
                await self.validator.update_scores(scores, valid_miner_uids)
                bt.logging.debug("update_scores completed")
                self.validator.last_scoring_block = current_block
                bt.logging.debug("score_miner_volumes completed successfully")

                if volumes:
                    try:
                        serializable_volumes = [
                            {
                                "uid": uid,
                                "volume": float(miner_volumes[str(uid)]),
                                "score": rewards[valid_miner_uids.index(uid)],
                            }
                            for uid in valid_miner_uids
                        ]
                        return JSONResponse(content=serializable_volumes)
                    except Exception:
                        bt.logging.error(
                            f"Exception serializing volumes:\n{traceback.format_exc()}"
                        )
                        return JSONResponse(content=[])
                return JSONResponse(content=[])
            except Exception:
                bt.logging.error(
                    f"Exception in update_scores:\n{traceback.format_exc()}"
                )
                return JSONResponse(content=[])
        except Exception:
            bt.logging.error(
                f"Critical exception in score_miner_volumes:\n{traceback.format_exc()}"
            )
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
