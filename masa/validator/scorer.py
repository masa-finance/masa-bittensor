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

    def format_miner_link(self, uid: int) -> str:
        """Format a miner's hotkey into a taostats URL."""
        hotkey = self.validator.metagraph.hotkeys[uid]
        return f"https://taostats.io/hotkey/{hotkey}"

    async def score_miner_volumes(self, current_block: int):
        try:
            bt.logging.debug("🔍 Starting score_miner_volumes...")
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
                    miner_stats = []
                    for uid in valid_miner_uids:
                        volume = miner_volumes[
                            str(uid)
                        ]  # Convert UID to string for lookup
                        reward = self.kurtosis_based_score(
                            volume, mean_volume, std_dev_volume
                        )
                        rewards.append(reward)
                        miner_stats.append((uid, volume, reward))
                        bt.logging.debug(
                            f"Miner {self.format_miner_link(uid)}: volume={volume}, reward={reward:.4f}"
                        )

                    # Sort miners by reward for top/bottom display
                    sorted_miners = sorted(
                        miner_stats, key=lambda x: x[2], reverse=True
                    )

                    # Display top 5 miners
                    bt.logging.info("+" + "=" * 50 + "+")
                    bt.logging.info(
                        "|" + " " * 15 + "TOP 5 MINERS BY REWARD" + " " * 15 + "|"
                    )
                    bt.logging.info("+" + "=" * 50 + "+")
                    for uid, volume, reward in sorted_miners[:5]:
                        bt.logging.info(
                            f"Miner: {uid}, Volume: {volume:.0f}, Reward: {reward:.4f}, Link: https://taostats.io/hotkey/{self.validator.metagraph.hotkeys[uid]}"
                        )

                    # Display bottom 5 miners
                    bt.logging.info("\n+" + "=" * 50 + "+")
                    bt.logging.info(
                        "|" + " " * 13 + "BOTTOM 5 MINERS BY REWARD" + " " * 13 + "|"
                    )
                    bt.logging.info("+" + "=" * 50 + "+")
                    for uid, volume, reward in sorted_miners[-5:]:
                        bt.logging.info(
                            f"Miner: {uid}, Volume: {volume:.0f}, Reward: {reward:.4f}, Link: https://taostats.io/hotkey/{self.validator.metagraph.hotkeys[uid]}"
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

                # Add summary statistics
                if valid_miner_uids:
                    total_volume = sum(
                        float(miner_volumes[str(uid)]) for uid in valid_miner_uids
                    )
                    avg_volume = total_volume / len(valid_miner_uids)
                    max_volume = max(
                        float(miner_volumes[str(uid)]) for uid in valid_miner_uids
                    )
                    min_volume = min(
                        float(miner_volumes[str(uid)]) for uid in valid_miner_uids
                    )
                    avg_reward = sum(rewards) / len(rewards)
                    max_reward = max(rewards)
                    min_reward = min(rewards)

                    bt.logging.info(f"Stats: Total Miners={len(valid_miner_uids)}")
                    bt.logging.info(f"Volume: Total={total_volume:.0f}")
                    bt.logging.info(f"Volume: Average={avg_volume:.0f}")
                    bt.logging.info(f"Volume: Min={min_volume:.0f}")
                    bt.logging.info(f"Volume: Max={max_volume:.0f}")
                    bt.logging.info(f"Score: Average={avg_reward:.4f}")
                    bt.logging.info(f"Score: Min={min_reward:.4f}")
                    bt.logging.info(f"Score: Max={max_reward:.4f}")

                bt.logging.success("Miner tweet volumes scoring complete")

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

    async def _process_responses(self, responses, miner_uids, random_keyword):
        """Process and validate miner responses."""
        all_valid_tweets = []
        total_errors = 0
        miner_stats = []
        unreachable_miners = []
        no_tweets_miners = []
        validation_errors = 0

        # Initialize masa-ai validator
        try:
            with SilentOutput():
                tweet_validator = TweetValidator()
                bt.logging.debug("Initialized masa-ai validator")
        except Exception as e:
            bt.logging.error(f"Failed to initialize masa-ai validator: {e}")
            tweet_validator = None

        for response, uid in zip(responses, miner_uids):
            hotkey = self.validator.metagraph.hotkeys[uid]
            taostats_link = f"https://taostats.io/hotkey/{hotkey}"

            if response is None or response.get("response") is None:
                unreachable_miners.append(uid)
                bt.logging.info(f"🔴 Miner {uid} | Unreachable | {taostats_link}")
                continue

            try:
                response_data = dict(response)
                resp = response_data.get("response")

                # Process the response
                valid_items, errors, valid = self._process_single_response(resp, uid)
                total_errors += errors

                if valid > 0:
                    # Log the initial count of tweets received
                    bt.logging.info(
                        f"📥 Miner {uid} | Received {valid} tweets for validation"
                    )

                    # Validate tweets with masa-ai
                    validated_tweets = []
                    validation_failures = []

                    for item in valid_items:
                        tweet = item.get("Tweet", {})
                        tweet_id = tweet.get("ID", "unknown")
                        tweet_text = tweet.get("Text", "")

                        # First check basic structure
                        if not self._validate_tweet_structure(item):
                            validation_failures.append(
                                {
                                    "tweet_id": tweet_id,
                                    "reason": "Invalid structure",
                                    "details": "Missing required fields",
                                }
                            )
                            continue

                        try:
                            if tweet_validator:
                                with SilentOutput():
                                    is_valid = tweet_validator.validate_tweet(
                                        tweet_text
                                    )
                                    if is_valid:
                                        validated_tweets.append(item)
                                        bt.logging.debug(
                                            f"✅ Tweet {tweet_id} passed masa-ai validation"
                                        )
                                    else:
                                        validation_failures.append(
                                            {
                                                "tweet_id": tweet_id,
                                                "reason": "Failed masa-ai validation",
                                                "text": (
                                                    tweet_text[:100] + "..."
                                                    if len(tweet_text) > 100
                                                    else tweet_text
                                                ),
                                            }
                                        )
                            else:
                                # Fallback to internal validation
                                if self._check_tweet_timestamp(
                                    tweet.get("Timestamp", 0)
                                ):
                                    validated_tweets.append(item)
                                    bt.logging.debug(
                                        f"✅ Tweet {tweet_id} passed timestamp validation"
                                    )
                                else:
                                    validation_failures.append(
                                        {
                                            "tweet_id": tweet_id,
                                            "reason": "Failed timestamp validation",
                                            "timestamp": tweet.get("Timestamp", 0),
                                        }
                                    )

                        except Exception as e:
                            validation_errors += 1
                            validation_failures.append(
                                {
                                    "tweet_id": tweet_id,
                                    "reason": "Validation error",
                                    "error": str(e),
                                }
                            )
                            continue

                    valid = len(validated_tweets)
                    if valid > 0:
                        miner_stats.append((uid, valid))
                        bt.logging.info(
                            f"🟢 Miner {uid} | {valid}/{len(valid_items)} tweets validated | {taostats_link}"
                        )
                    else:
                        no_tweets_miners.append(uid)
                        bt.logging.info(
                            f"🟡 Miner {uid} | No valid tweets | {taostats_link}"
                        )
                        if validation_failures:
                            bt.logging.info(f"❌ Validation failures for miner {uid}:")
                            for failure in validation_failures:
                                bt.logging.info(
                                    f"   Tweet {failure['tweet_id']}: {failure['reason']}"
                                )
                                if "text" in failure:
                                    bt.logging.info(f"      Content: {failure['text']}")
                                if "timestamp" in failure:
                                    bt.logging.info(
                                        f"      Timestamp: {failure['timestamp']}"
                                    )
                                if "error" in failure:
                                    bt.logging.info(f"      Error: {failure['error']}")
                else:
                    no_tweets_miners.append(uid)
                    bt.logging.info(
                        f"🟡 Miner {uid} | No tweets received | {taostats_link}"
                    )

            except Exception as e:
                bt.logging.error(
                    f"❌ Miner {uid} | Processing error: {str(e)} | {taostats_link}"
                )
                continue

        # Summary section
        bt.logging.info("Volume Check Results:")
        bt.logging.info(f"└─ Query: {random_keyword}")
        bt.logging.info(
            f"└─ Miners: {len(miner_stats)} active, {len(unreachable_miners)} unreachable, {len(no_tweets_miners)} no tweets"
        )

        if miner_stats:
            miner_summary = ", ".join(f"{uid}:{count}" for uid, count in miner_stats)
            bt.logging.info(f"└─ Tweets per miner: {miner_summary}")

        validation_method = "masa-ai" if tweet_validator else "internal"
        bt.logging.info(
            f"└─ Validation: {validation_method} | Errors: {validation_errors}"
        )
        bt.logging.info(
            f"└─ Total tweets: {len(all_valid_tweets)} valid, {total_errors} errors"
        )
