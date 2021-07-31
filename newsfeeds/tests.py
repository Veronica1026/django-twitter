from newsfeeds.services import NewsFeedService
from testing.testcases import TestCase
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_client import RedisClient


class NewsfeedServiceTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.bob = self.create_user('bob')
        self.alex = self.create_user('alex')

    def test_get_user_newsfeeds(self):
        newsfeed_ids = []
        for i in range(3):
            tweet = self.create_tweet(self.alex)
            newsfeed = self.create_newsfeed(self.bob, tweet)
            newsfeed_ids.append(newsfeed.id)
        newsfeed_ids = newsfeed_ids[::-1]

        # cache miss
        newsfeeds = NewsFeedService.get_cached_newsfeeds(self.bob.id)
        self.assertEqual([f.id for f in newsfeeds], newsfeed_ids)

        # cache hit
        newsfeeds = NewsFeedService.get_cached_newsfeeds(self.bob.id)
        self.assertEqual([f.id for f in newsfeeds], newsfeed_ids)

        # cache update
        tweet = self.create_tweet(self.bob)
        new_newsfeed = self.create_newsfeed(self.bob, tweet)
        newsfeeds = NewsFeedService.get_cached_newsfeeds(self.bob.id)
        newsfeed_ids.insert(0, new_newsfeed.id)
        self.assertEqual([f.id for f in newsfeeds], newsfeed_ids)

    def test_create_new_newsfeeds_before_get_cached_newsfeeds(self):
        feed1 = self.create_newsfeed(self.bob, self.create_tweet(self.bob))

        RedisClient.clear()
        conn = RedisClient.get_connection()

        key = USER_NEWSFEEDS_PATTERN.format(user_id=self.bob.id)
        self.assertEqual(conn.exists(key), False)
        feed2 = self.create_newsfeed(self.bob, self.create_tweet(self.bob))
        self.assertEqual(conn.exists(key), True)

        feeds = NewsFeedService.get_cached_newsfeeds(self.bob.id)
        self.assertEqual([f.id for f in feeds], [feed2.id, feed1.id])
