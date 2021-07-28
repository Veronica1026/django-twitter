def push_tweet_to_cache(sender, instance, created, **kwargs):
    if not created:
        return
    from tweets.service import TweetService
    TweetService.push_tweet_to_cache(instance)