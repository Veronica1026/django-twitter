from gatekeeper.models import GateKeeper
from newsfeeds.models import NewsFeed, HBaseNewsFeed
from newsfeeds.services import NewsFeedService
from newsfeeds.tasks import fanout_newsfeeds_main_task
from testing.testcases import TestCase
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_client import RedisClient


class NewsfeedServiceTests(TestCase):

    def setUp(self):
        super(NewsfeedServiceTests, self).setUp()
        self.bob = self.create_user('bob')
        self.alex = self.create_user('alex')

    def test_get_user_newsfeeds(self):
        newsfeed_timestamps = []
        for i in range(3):
            tweet = self.create_tweet(self.alex)
            newsfeed = self.create_newsfeed(self.bob, tweet)
            newsfeed_timestamps.append(newsfeed.created_at)
        newsfeed_timestamps = newsfeed_timestamps[::-1]

        # cache miss
        newsfeeds = NewsFeedService.get_cached_newsfeeds(self.bob.id)
        self.assertEqual([f.created_at for f in newsfeeds], newsfeed_timestamps)

        # cache hit
        newsfeeds = NewsFeedService.get_cached_newsfeeds(self.bob.id)
        self.assertEqual([f.created_at for f in newsfeeds], newsfeed_timestamps)

        # cache update
        tweet = self.create_tweet(self.bob)
        new_newsfeed = self.create_newsfeed(self.bob, tweet)
        newsfeeds = NewsFeedService.get_cached_newsfeeds(self.bob.id)
        newsfeed_timestamps.insert(0, new_newsfeed.created_at)
        self.assertEqual([f.created_at for f in newsfeeds], newsfeed_timestamps)

    def test_create_new_newsfeeds_before_get_cached_newsfeeds(self):
        feed1 = self.create_newsfeed(self.bob, self.create_tweet(self.bob))

        self.clear_cache()
        conn = RedisClient.get_connection()

        key = USER_NEWSFEEDS_PATTERN.format(user_id=self.bob.id)
        self.assertEqual(conn.exists(key), False)
        feed2 = self.create_newsfeed(self.bob, self.create_tweet(self.bob))
        self.assertEqual(conn.exists(key), True)

        feeds = NewsFeedService.get_cached_newsfeeds(self.bob.id)
        self.assertEqual([f.created_at for f in feeds], [feed2.created_at, feed1.created_at])


class NewsFeedTaskTests(TestCase):

    def setUp(self):
        super(NewsFeedTaskTests, self).setUp()
        self.bob = self.create_user('bob')
        self.alex = self.create_user('alex')

    def test_fanout_main_task(self):
        tweet = self.create_tweet(self.bob, 'tweet 1')
        self.create_friendship(self.alex, self.bob)
        if GateKeeper.is_switched_on('switch_newsfeed_to_hbase'):
            msg = fanout_newsfeeds_main_task(tweet.id, tweet.timestamp, self.bob.id)
            self.assertEqual(1 + 1, len(HBaseNewsFeed.filter(prefix=(None, None))))
        else:
            msg = fanout_newsfeeds_main_task(tweet.id, tweet.created_at, self.bob.id)
            self.assertEqual(1 + 1, NewsFeed.objects.count())

        self.assertEqual(msg, '1 newsfeeds going to fanout, 1 batches created.')

        cached_list = NewsFeedService.get_cached_newsfeeds(self.bob.id)
        self.assertEqual(len(cached_list), 1)

        for i in range(2):
            user = self.create_user('user{}'.format(i))
            self.create_friendship(user, self.bob)
        tweet = self.create_tweet(self.bob, 'tweet 2')
        if GateKeeper.is_switched_on('switch_newsfeed_to_hbase'):
            msg = fanout_newsfeeds_main_task(tweet.id, tweet.timestamp, self.bob.id)
            self.assertEqual(4 + 2, len(HBaseNewsFeed.filter(prefix=(None, None))))
        else:
            msg = fanout_newsfeeds_main_task(tweet.id, tweet.created_at, self.bob.id)
            self.assertEqual(4 + 2, NewsFeed.objects.count())

        self.assertEqual(msg, '3 newsfeeds going to fanout, 1 batches created.')
        cached_list = NewsFeedService.get_cached_newsfeeds(self.bob.id)
        self.assertEqual(len(cached_list), 2)

        user = self.create_user('another user')
        self.create_friendship(user, self.bob)
        tweet = self.create_tweet(self.bob, 'tweet 3')
        if GateKeeper.is_switched_on('switch_newsfeed_to_hbase'):
            msg = fanout_newsfeeds_main_task(tweet.id, tweet.timestamp, self.bob.id)
            self.assertEqual(8 + 3, len(HBaseNewsFeed.filter(prefix=(None, None))))
        else:
            msg = fanout_newsfeeds_main_task(tweet.id, tweet.created_at, self.bob.id)
            self.assertEqual(8 + 3, NewsFeed.objects.count())
        self.assertEqual(msg, '4 newsfeeds going to fanout, 2 batches created.')
        cached_list = NewsFeedService.get_cached_newsfeeds(self.bob.id)
        self.assertEqual(len(cached_list), 3)
        cached_list = NewsFeedService.get_cached_newsfeeds(self.alex.id)
        self.assertEqual(len(cached_list), 3)
