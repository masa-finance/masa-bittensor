from masa.types.twitter import TwitterFollowerObject

def followers_parser(followers):
    return [
        [TwitterFollowerObject(**follower) for follower in response]
        for response in followers  # Each response is a list of dictionaries
    ]