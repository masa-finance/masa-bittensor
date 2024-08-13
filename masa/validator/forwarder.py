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

from masa.utils.uids import get_random_uids
import bittensor as bt
import torch
from collections import defaultdict
import math
from sklearn.cluster import KMeans
# this forwarder needs to able to handle multiple requests, driven off of an API request


class Forwarder:
    def __init__(self, validator):
        self.validator = validator
        self.minimum_accepted_score = 0.8

    async def forward(
        self,
        request,
        parser_object=None,
        parser_method=None,
        timeout=5,
        source_method=None,
    ):
        miner_uids = await get_random_uids(
            self.validator, k=self.validator.config.neuron.sample_size
        )

        bt.logging.info("Calling UIDS -----------------------------------------")
        bt.logging.info(miner_uids)

        if miner_uids is None:
            return []

        synapses = await self.validator.dendrite(
            axons=[self.validator.metagraph.axons[uid] for uid in miner_uids],
            synapse=request,
            deserialize=False,
            timeout=timeout,
        )

        responses = [synapse.response for synapse in synapses]

        # Filter and parse valid responses
        valid_responses, valid_miner_uids = self.sanitize_responses_and_uids(
            responses, miner_uids=miner_uids
        )
        parsed_responses = responses

        bt.logging.trace("Parsed responses -----------------------------------------")
        bt.logging.trace(parsed_responses)

        if parser_object:
            parsed_responses = [
                parser_object(**response) for response in valid_responses
            ]
        elif parser_method:
            parsed_responses = parser_method(valid_responses)

        process_times = [
            synapse.dendrite.process_time
            for synapse, uid in zip(synapses, miner_uids)
            if uid in valid_miner_uids
        ]

        source_of_truth = await self.get_source_of_truth(
            responses=parsed_responses,
            miner_uids=miner_uids,
            source_method=source_method,
            query=request.query,
        )

        # Score responses
        rewards = self.get_rewards(
            responses=parsed_responses, source_of_truth=source_of_truth
        )
        # Update the scores based on the rewards
        if len(valid_miner_uids) > 0:
            self.validator.update_scores(rewards, valid_miner_uids)
            if self.validator.should_set_weights():
                try:
                    self.validator.set_weights()
                except Exception as e:
                    bt.logging.error(f"Failed to set weights: {e}")

        # Add corresponding uid to each response
        responses_with_metadata = [
            {
                "response": response,
                "uid": int(uid.item()),
                "score": score.item(),
                "latency": latency,
            }
            for response, latency, uid, score in zip(
                parsed_responses, process_times, valid_miner_uids, rewards
            )
        ]

        responses_with_metadata.sort(key=lambda x: (-x["score"], x["latency"]))
        return responses_with_metadata

    def get_rewards(self, responses: dict, source_of_truth: dict) -> torch.FloatTensor:

        combined_responses = responses.copy()
        combined_responses.append(source_of_truth)

        embeddings = self.validator.model.encode(
            [str(response) for response in combined_responses]
        )

        num_clusters = min(len(combined_responses), 2)
        clustering_model = KMeans(n_clusters=num_clusters)
        clustering_model.fit(embeddings)
        cluster_labels = clustering_model.labels_

        source_of_truth_label = cluster_labels[-1] if len(cluster_labels) > 0 else None
        bt.logging.info("Source of truth -----------------------------------------")
        bt.logging.info(source_of_truth)
        bt.logging.info(f"Source of truth label: {source_of_truth_label}")
        bt.logging.info(f"labels: {cluster_labels}")
        rewards_list = [
            (
                1
                if cluster_labels[i] == source_of_truth_label
                else self.calculate_reward(response, source_of_truth)
            )
            for i, response in enumerate(responses)
        ]

        bt.logging.info("REWARDS LIST ----------------------------------------------")
        bt.logging.info(rewards_list)

        return torch.FloatTensor(rewards_list).to(self.validator.device)

    def score_dicts_difference(self, initialScore, dict1, dict2):
        score = initialScore

        if not isinstance(dict1, dict) and not isinstance(dict2, dict):
            if dict1 != dict2:
                return max(score - 0.1, 0)
            else:
                return max(score, 0)

        for key in dict1.keys():
            if key not in dict2 or dict2[key] is None:
                score -= 0.1
            elif isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                score = self.score_dicts_difference(score, dict1[key], dict2[key])
            elif isinstance(dict1[key], list) and isinstance(dict2[key], list):
                if len(dict1[key]) != len(dict2[key]):
                    length_difference = abs(len(dict1[key]) - len(dict2[key]))
                    score -= 0.1 * (1 + length_difference)
                else:
                    for item1, item2 in zip(dict1[key], dict2[key]):
                        score = self.score_dicts_difference(score, item1, item2)
            elif str(dict1[key]) != str(dict2[key]):
                score -= 0.1

        return max(score, 0)

    def calculate_reward(self, response: dict, source_of_truth: dict) -> float:

        # Return a reward of 0.0 if the response is None
        if response is None:
            return 0.0

        response = {"response": response}

        score = self.score_dicts_difference(1, source_of_truth, response)
        return max(score, 0)  # Ensure the score doesn't go below 0

    def sanitize_responses_and_uids(self, responses, miner_uids):
        valid_responses = [response for response in responses if response is not None]
        valid_miner_uids = [
            miner_uids[i]
            for i, response in enumerate(responses)
            if response is not None
        ]
        return valid_responses, valid_miner_uids

    async def get_source_of_truth(self, responses, miner_uids, source_method, query):
        responses_str = [str(response) for response in responses]
        weighted_responses = defaultdict(float)
        most_common_response = None
        count_high_score_uids = sum(
            1
            for uid in miner_uids
            if self.validator.scores[uid] >= self.minimum_accepted_score
        )
        bt.logging.info(
            f"Number of UIDs with score greater than the minimum accepted: {count_high_score_uids}"
        )

        if count_high_score_uids > 10:
            for response, uid in zip(responses_str, miner_uids):
                score = self.validator.scores[uid]
                exponential_weight = math.exp(score)

                weighted_responses[response] += exponential_weight

            most_common_response = max(weighted_responses, key=weighted_responses.get)
        else:
            if source_method:
                most_common_response = source_method(query)

        if isinstance(most_common_response, str):
            try:
                most_common_response = eval(most_common_response)
            except Exception as e:
                bt.logging.error(
                    f"Failed to transform most_common_response to dict: {e}"
                )
                most_common_response = {}

        most_common_response = {"response": most_common_response}

        return most_common_response
