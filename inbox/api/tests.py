from notifications.models import Notification
from testing.testcases import TestCase


COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'
NOTIFICATION_URL = '/api/notifications/'


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


class NotificationApiTests(TestCase):

    def setUp(self):
        self.bob, self.bob_client = self.create_user_and_client('bob')
        self.alex, self.alex_client = self.create_user_and_client('alex')
        self.bob_tweet = self.create_tweet(self.bob)

    def test_unread_count(self):
        self.alex_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.bob_tweet.id,
        })

        url = '/api/notifications/unread-count/'
        # post not allowed
        response = self.bob_client.post(url)
        self.assertEqual(response.status_code, 405)
        # get ok
        response = self.bob_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['unread_count'], 1)

        comment = self.create_comment(self.bob, self.bob_tweet)
        self.alex_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })
        # recipient can see the notifications
        response = self.bob_client.get(url)
        self.assertEqual(response.data['unread_count'], 2)

        # non recipient cannot see the notifications
        response = self.alex_client.get(url)
        self.assertEqual(response.data['unread_count'], 0)

    def test_mark_all_as_read(self):
        self.alex_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.bob_tweet.id,
        })
        comment = self.create_comment(self.bob, self.bob_tweet)
        self.alex_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })

        unread_url = '/api/notifications/unread-count/'
        response = self.bob_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 2)

        mark_url = '/api/notifications/mark-all-as-read/'

        # get not allowed
        response = self.bob_client.get(mark_url)
        self.assertEqual(response.status_code, 405)

        # others post not working
        response = self.alex_client.post(mark_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['marked_count'], 0)
        response = self.bob_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 2)
        # recipient post ok
        response = self.bob_client.post(mark_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['marked_count'], 2)
        response = self.bob_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 0)

    def test_list(self):
        self.alex_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.bob_tweet.id,
        })
        comment = self.create_comment(self.bob, self.bob_tweet)
        self.alex_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })

        # anonymous user cannot visit the api
        response = self.anonymous_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 403)
        # alex has no notification
        response = self.alex_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        # bob can see two notifications
        response = self.bob_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        # after mark unread, bob can see one notification
        notification = self.bob.notifications.first()
        notification.unread = False
        notification.save()
        # in total bob has two notifications
        response = self.bob_client.get(NOTIFICATION_URL)
        self.assertEqual(response.data['count'], 2)
        # now both read and unread notification count is one
        response = self.bob_client.get(NOTIFICATION_URL, {
            'unread': True,
        })
        self.assertEqual(response.data['count'], 1)
        response = self.bob_client.get(NOTIFICATION_URL, {
            'unread': False,
        })
        self.assertEqual(response.data['count'], 1)

    def test_update(self):
        self.alex_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'object_id': self.bob_tweet.id,
        })
        comment = self.create_comment(self.bob, self.bob_tweet)
        self.alex_client.post(LIKE_URL, {
            'content_type': 'comment',
            'object_id': comment.id,
        })

        notification = self.bob.notifications.first()

        url = '/api/notifications/{}/'.format(notification.id)
        # cannot use post, we need put
        response = self.bob_client.post(url, {'unread': False})
        self.assertEqual(response.status_code, 405)

        # cannot update by others, for anonymous user it's 403
        response = self.anonymous_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, 403)
        # for other user rather than the recipient, it's 404,
        # since we try to find the corresponding object according to user id and object id, but cannot find it
        response = self.alex_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, 404)

        # marked as read successfully
        response = self.bob_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, 200)
        unread_url = '/api/notifications/unread-count/'
        response = self.bob_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 1)

        # mark as unread again
        response = self.bob_client.put(url, {'unread': True})
        response = self.bob_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 2)

        # must have unread in request data
        response = self.bob_client.put(url, {'verb': 'new_verb'})
        self.assertEqual(response.status_code, 400)

        # cannot modify other information
        response = self.bob_client.put(url, {
            'unread': False,
            'verb': 'new_verb',
        })
        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertNotEqual(notification.verb, 'new_verb')



