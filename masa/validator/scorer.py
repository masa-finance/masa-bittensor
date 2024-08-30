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
from collections import defaultdict
import math
from sklearn.cluster import KMeans
from masa.api.request import Request, RequestType


class Scorer:
    def __init__(self, validator):
        self.validator = validator
        # self.minimum_accepted_score = 0.8

    async def get_miner_responses_for_scoring(self):
        dendrite = bt.dendrite(wallet=self.validator.wallet)
        request = Request(
            query="(bitcoin) since:2024-08-27",
            count=1,
            type=RequestType.TWITTER_TWEETS.value,
        )
        responses = []
        sample_size = self.validator.config.neuron.sample_size
        for i in range(0, len(self.validator.metagraph.axons), sample_size):
            batch = self.validator.metagraph.axons[i : i + sample_size]
            batch_responses = await dendrite(
                batch,
                request,
                deserialize=False,
                timeout=15,
            )
            responses.extend(batch_responses)

        # return responses

        formatted_responses = []
        for i, response in enumerate(responses):
            response_dict = dict(response)
            formatted_response = {
                "uid": i,
                "total_size": response_dict.get("total_size", None),
                "status_code": dict(response_dict["dendrite"]).get("status_code", None),
                "status_message": dict(response_dict["dendrite"]).get(
                    "status_message", None
                ),
                "response": response_dict.get("response", None),
            }
            formatted_responses.append(formatted_response)
        return formatted_responses

    def get_rewards(self, responses: dict, source_of_truth: dict) -> torch.FloatTensor:

        combined_responses = responses.copy()
        if "response" in source_of_truth:
            combined_responses.append(source_of_truth["response"])
        else:
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

        similarity_percentages = [
            self.calculate_similarity_percentage(embeddings[i], embeddings[-1])
            for i in range(len(responses))
        ]
        bt.logging.info(f"Similarity percentages: {similarity_percentages}")

        rewards_list = [
            (
                1
                if cluster_labels[i] == source_of_truth_label
                else similarity_percentages[i] / 100
            )
            for i, response in enumerate(responses)
        ]

        bt.logging.info("REWARDS LIST ----------------------------------------------")
        bt.logging.info(rewards_list)

        return torch.FloatTensor(rewards_list).to(self.validator.device)

    def calculate_similarity_percentage(self, response_embedding, source_embedding):
        # Calculate the cosine similarity between the response and the source of truth
        cosine_similarity = torch.nn.functional.cosine_similarity(
            torch.tensor(response_embedding).unsqueeze(0),
            torch.tensor(source_embedding).unsqueeze(0),
        ).item()
        # Convert cosine similarity to percentage
        similarity_percentage = (cosine_similarity + 1) / 2 * 100
        return similarity_percentage

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
            if uid in self.validator.scores
            and self.validator.scores[uid] >= self.minimum_accepted_score
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
