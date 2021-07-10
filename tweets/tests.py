from datetime import timedelta
from testing.testcases import TestCase
from tweets.constants import TweetPhotoStatus
from tweets.models import TweetPhoto
from utils.time_helpers import utc_now


class TweetsTests(TestCase):
    def setUp(self):
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

