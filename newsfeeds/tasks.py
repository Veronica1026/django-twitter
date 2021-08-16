from celery import shared_task
from friendships.services import FriendshipService
from newsfeeds.constants import FANOUT_BATCH_SIZE
from newsfeeds.models import NewsFeed
from utils.time_constants import ONE_HOUR


@shared_task(routing_key='newsfeeds', time_limit=ONE_HOUR)
def fanout_newsfeeds_batch_task(tweet_id, follower_ids):
    # we put import inside to avoid circular dependency
    from newsfeeds.services import NewsFeedService

    # wrong thing to do:
    # don't put db operations inside for loop!!! Very low efficiency
    # for follower_id in follower_ids:
    #     NewsFeed.objects.create(user_id=follower_id, tweet_id=tweet_id)
    # right thing to do: user bulk_create, which combines all the insertion into one single query
    newsfeeds = [
        NewsFeed(user_id=follower_id, tweet_id=tweet_id)
        for follower_id in follower_ids
    ]
    NewsFeed.objects.bulk_create(newsfeeds)

    # bulk_create will not trigger the signal of post_save
    # so we need to manually push them to cache
    for newsfeed in newsfeeds:
        NewsFeedService.push_newsfeeds_to_cache(newsfeed)

    return "{} newsfeeds created".format(len(newsfeeds))


@shared_task(routing_key='default', time_limit=ONE_HOUR)
def fanout_newsfeeds_main_task(tweet_id, tweet_user_id):
    # we first create the newsfeed for the publisher, so that user can see the post
    NewsFeed.objects.create(user_id=tweet_user_id, tweet_id=tweet_id)

    # retrieve all the follower id, and split into batches
    follower_ids = FriendshipService.get_follower_ids(tweet_user_id)
    index = 0
    while index < len(follower_ids):
        batch_ids = follower_ids[index: index + FANOUT_BATCH_SIZE]
        fanout_newsfeeds_batch_task.delay(tweet_id, batch_ids)
        index += FANOUT_BATCH_SIZE

    return '{} newsfeeds going to fanout, {} batches created.'.format(
        len(follower_ids),
        (len(follower_ids) - 1) // FANOUT_BATCH_SIZE + 1,
    )
