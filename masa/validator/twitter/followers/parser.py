from masa.types.twitter import TwitterFollowerObject


def followers_parser(follower_responses):
    return [
        [TwitterFollowerObject(**follower) for follower in response]
        for response in follower_responses  # Each response is a list of dictionaries
    ]
