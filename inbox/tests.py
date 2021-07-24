from testing.testcases import TestCase
from inbox.services import NotificationService
from notifications.models import Notification


class NotificationServiceTest(TestCase):

    def setUp(self):
        self.clear_cache()
        self.bob = self.create_user('bob')
        self.alex = self.create_user('alex')
        self.bob_tweet = self.create_tweet(self.bob)

    def test_send_comment_notification(self):
        # do not dispatch notification if tweet.user = comment.user
        comment = self.create_comment(self.bob, self.bob_tweet)
        NotificationService.send_comment_notification(comment)
        self.assertEqual(Notification.objects.count(), 0)

        # dispatch notification if tweet user != comment user
        comment = self.create_comment(self.alex, self.bob_tweet)
        NotificationService.send_comment_notification(comment)
        self.assertEqual(Notification.objects.count(), 1)

    def test_send_like_notifications(self):
        # do not dispatch notification if tweet user == like user
        like = self.create_like(self.bob, self.bob_tweet)
        NotificationService.send_like_notification(like)
        self.assertEqual(Notification.objects.count(), 0)

        # dispatch notification if tweet user != comment user
        comment = self.create_comment(self.alex, self.bob_tweet)
        like = self.create_like(self.bob, comment)
        NotificationService.send_like_notification(like)
        self.assertEqual(Notification.objects.count(), 1)
