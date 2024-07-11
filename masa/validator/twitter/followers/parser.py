from masa.types.twitter import TwitterFollowerObject


def followers_parser(follower_responses):
    return [
        [TwitterFollowerObject(**follower) for follower in response if isinstance(follower, dict)]
        for response in follower_responses  # Each response is a list of dictionaries
    ]
