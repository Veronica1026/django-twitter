from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_helper import RedisHelper


class NewsFeedService(object):

    @classmethod
    def fanout_to_followers(cls, tweet):
        # 错误的方法
        # 不可以将数据库操作放在 for 循环里面，效率会非常低
        # for follower in FriendshipService.get_followers(tweet.user):
        #     NewsFeed.objects.create(
        #         user=follower,
        #         tweet=tweet,
        #     )

        # 正确的方法：使用 bulk_create，会把 insert 语句合成一条
        newsfeeds = [
            NewsFeed(user=follower, tweet=tweet)
            for follower in FriendshipService.get_followers(tweet.user)
        ]
        # 发帖人自己也应该能看到自己发的帖子
        newsfeeds.append(NewsFeed(user=tweet.user, tweet=tweet))
        NewsFeed.objects.bulk_create(newsfeeds)

        # bulk_create will not trigger the signal of post_save
        # so we need to manually push them to cache
        for newsfeed in newsfeeds:
            cls.push_newsfeeds_to_cache(newsfeed)

    @classmethod
    def get_cached_newsfeeds(cls, user_id):
        queryset = NewsFeed.objects.filter(user_id=user_id).order_by('-created_at')
        key = USER_NEWSFEEDS_PATTERN.format(user_id=user_id)
        return RedisHelper.load_objects(key, queryset)

    @classmethod
    def push_newsfeeds_to_cache(cls, newsfeed):
        queryset = NewsFeed.objects.filter(user_id=newsfeed.user_id).order_by('-created_at')
        key = USER_NEWSFEEDS_PATTERN.format(user_id=newsfeed.user.id)
        RedisHelper.push_objects(key, newsfeed, queryset)
