import torch
import bittensor as bt

from masa.types.twitter import TwitterProfileObject


def reward(query: str, response: TwitterProfileObject) -> float:
    # Return a reward of 0.0 if the response is None
    if response is None:
        return 0.0 
    bt.logging.info(f"Getting username from {response}")
    # Extract username and userID from the response, defaulting to empty string and None respectively
    username = response.get("Username", "")
    userID = response.get("UserID", None)
    bt.logging.info(f"Calculating reward for response {username.lower()}")
    
    # Return a reward of 1 if the username matches the query and userID is not None, otherwise return 0
    if username.lower() == query.lower() and userID != None:
        return 1
    else:
        return 0

def get_rewards(
    self,
    query: str,
    responses: TwitterProfileObject,
) -> torch.FloatTensor:
    bt.logging.info(f"Getting rewards...")
    return torch.FloatTensor(
        [reward(query, response) for response in responses]
    ).to(self.device) 

