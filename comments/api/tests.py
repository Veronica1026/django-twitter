from comments.models import Comment
from django.utils import timezone
from rest_framework.test import APIClient
from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
COMMENT_DETAIL_URL = '/api/comments/{}/'


class CommentApiTests(TestCase):

    def setUp(self):
        self.bob = self.create_user('bob')
        self.bob_client = APIClient()
        self.bob_client.force_authenticate(self.bob)
        self.alex = self.create_user('alex')
        self.alex_client = APIClient()
        self.alex_client.force_authenticate(self.alex)

        self.tweet = self.create_tweet(self.bob)

    def test_create(self):
        # cannot comment anonymously
        response = self.anonymous_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, 403)

        # must have parameters
        response = self.bob_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, 400)

        # only tweet id in parameters is not enough
        response = self.bob_client.post(COMMENT_URL, {'tweet_id': self.tweet.id})
        self.assertEqual(response.status_code, 400)

        # only content in parameters is not enough
        response = self.bob_client.post(COMMENT_URL, {'content': '1'})
        self.assertEqual(response.status_code, 400)

        # content cannot be too long
        response = self.bob_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1' * 141,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('content' in response.data['errors'], True)

        # both tweet id and content are needed
        response = self.bob_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user']['id'], self.bob.id)
        self.assertEqual(response.data['tweet_id'], self.tweet.id)
        self.assertEqual(response.data['content'], '1')

    def test_destroy(self):
        comment = self.create_comment(self.bob, self.tweet)
        url = COMMENT_DETAIL_URL.format(comment.id)

        # cannot delete when anonymous
        response = self.anonymous_client.delete(url)
        self.assertEqual(response.status_code, 403)

        # cannot delete when you are not the creater of the comment
        response = self.alex_client.delete(url)
        self.assertEqual(response.status_code, 403)

        # can delete if the comment is written by yourself
        count = Comment.objects.count()
        response = self.bob_client.delete(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), count - 1)

    def test_update(self):
        comment = self.create_comment(self.bob, self.tweet, 'original content')
        another_tweet = self.create_tweet(self.alex)
        url = COMMENT_DETAIL_URL.format(comment.id)

        # using put, but anonymous, cannot update
        response = self.anonymous_client.put(url, {'content': 'new content'})
        self.assertEqual(response.status_code, 403)

        # cannot update if you are not the creator of the comment
        response = self.alex_client.put(url, {'content': 'new content'})
        self.assertEqual(response.status_code, 403)

        # update cache
        comment.refresh_from_db()

        self.assertNotEqual(comment.content, 'new content')
        # cannot update other info except content. Silent process
        before_updated_at = comment.updated_at
        before_created_at = comment.created_at
        now = timezone.now()

        response = self.bob_client.put(url, {
            'content': 'new content',
            'user_id': self.alex.id,
            'tweet_id': another_tweet.id,
            'created_at': now,
        })
        self.assertEqual(response.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'new content')
        self.assertEqual(comment.user, self. bob)
        self.assertEqual(comment.tweet, self.tweet)
        self.assertEqual(comment.created_at, before_created_at)
        self.assertNotEqual(comment.created_at, now)
        self.assertNotEqual(comment.updated_at, before_updated_at)
