from celery import shared_task
from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed
from tweets.models import Tweet
from utils.time_constants import ONE_HOUR


@shared_task(time_limit=ONE_HOUR)
def fanout_newsfeeds_task(tweet_id):
    # we put import inside to avoid circular dependency
    from newsfeeds.services import NewsFeedService

    # wrong thing to do:
    # don't put db operations inside for loop!!! Very low efficiency
    # for follower in FriendshipService.get_followers(tweet.user):
    #     NewsFeed.objects.create(
    #         user=follower,
    #         tweet=tweet,
    #     )
    # right thing to do: user bulk_create, which combines all the insertion into one single query
    tweet = Tweet.objects.get(id=tweet_id)
    newsfeeds = [
        NewsFeed(user=follower, tweet=tweet)
        for follower in FriendshipService.get_followers(tweet.user)
    ]
    # the person who publishes the tweet should also be able to view his tweet
    # so we add it to his own newsfeed too
    newsfeeds.append(NewsFeed(user=tweet.user, tweet=tweet))
    NewsFeed.objects.bulk_create(newsfeeds)

    # bulk_create will not trigger the signal of post_save
    # so we need to manually push them to cache
    for newsfeed in newsfeeds:
        NewsFeedService.push_newsfeeds_to_cache(newsfeed)
