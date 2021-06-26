from notifications.models import Notification
from testing.testcases import TestCase


COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'


class NotificationTests(TestCase):

    def setUp(self):
        self.bob, self.bob_client = self.create_user_and_client('bob')
        self.alex, self.alex_client = self.create_user_and_client('alex')
        self.alex_tweet = self.create_tweet(self.alex)

    def test_comment_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.bob_client.post(COMMENT_URL, {
            'tweet_id': self.alex_tweet.id,
            'content': 'aha!',
        })
        self.assertEqual(Notification.objects.count(), 1)

    def test_like_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        response = self.bob_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.alex_tweet.id,
        })
        print(response.status_code)
        self.assertEqual(Notification.objects.count(), 1)

        # test duplicate like would not produce duplicate notification
        self.bob_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.alex_tweet.id,
        })
        self.assertEqual(Notification.objects.count(), 1)

