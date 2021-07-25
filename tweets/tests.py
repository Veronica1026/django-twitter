from datetime import timedelta
from testing.testcases import TestCase
from tweets.constants import TweetPhotoStatus
from tweets.models import TweetPhoto
from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer
from utils.time_helpers import utc_now


class TweetsTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.bob = self.create_user('bob')
        self.tweet = self.create_tweet(self.bob, content='bob is here for you')

    def test_hours_to_now(self):
        self.tweet.created_at = utc_now() - timedelta(hours=10)
        self.tweet.save()
        self.assertEqual(self.tweet.hours_to_now, 10)

    def test_like_set(self):
        self.create_like(self.bob, self.tweet)
        self.assertEqual(self.tweet.like_set.count(), 1)

        self.create_like(self.bob, self.tweet)
        self.assertEqual(self.tweet.like_set.count(), 1)

        alex = self.create_user('alex')
        self.create_like(alex, self.tweet)
        self.assertEqual(self.tweet.like_set.count(), 2)

    def test_create_photo(self):
        # test we can successfully create tweet object
        photo = TweetPhoto.objects.create(
            tweet=self.tweet,
            user=self.bob,
        )
        self.assertEqual(photo.user, self.bob)
        self.assertEqual(photo.status, TweetPhotoStatus.PENDING)
        self.assertEqual(self.tweet.tweetphoto_set.count(), 1)

    def test_cache_tweet_in_redis(self):
        tweet = self.create_tweet(self.bob)
        conn = RedisClient.get_connection()
        serialized_data = DjangoModelSerializer.serialize(tweet)
        conn.set(f'tweet:{tweet.id}', serialized_data)
        data = conn.get(f'tweet:not_exists')
        self.assertEqual(data, None)

        data = conn.get(f'tweet:{tweet.id}')
        cached_tweet = DjangoModelSerializer.deserialize(data)
        self.assertEqual(tweet, cached_tweet)

