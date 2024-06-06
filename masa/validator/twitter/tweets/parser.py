from masa.types.twitter import TwitterTweetObject

def tweets_parser(tweets):
    return [
        [TwitterTweetObject(**tweet) for tweet in response]
        for response in tweets  # Each response is a list of dictionaries
    ]