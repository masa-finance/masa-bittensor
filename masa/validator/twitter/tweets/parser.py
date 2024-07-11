from masa.types.twitter import TwitterTweetObject


def tweets_parser(tweet_responses):
    return [
        [TwitterTweetObject(**tweet) for tweet in response if isinstance(tweet, dict)]
        for response in tweet_responses  # Each response is a list of dictionaries
    ]
