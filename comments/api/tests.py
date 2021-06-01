from comments.models import Comment
from django.utils import timezone
from rest_framework.test import APIClient
from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
COMMENT_DETAIL_URL = '/api/comments/{}/'
TWEET_LIST_API = '/api/tweets/'
TWEET_DETAIL_API = '/api/tweets/{}/'
NEWSFEED_LIST_API = '/api/newsfeeds/'


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

    def test_list(self):
        # must have tweet_id
        response = self.anonymous_client.get(COMMENT_URL)
        self.assertEqual(response.status_code, 400)

        # success if we have tweet_id
        # now there is no comments
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['comments']), 0)

        # comments are sorted according to timestamp asc
        self.create_comment(self.bob, self.tweet, 'b1')
        self.create_comment(self.alex, self.tweet, 'a1')
        self.create_comment(self.alex, self.create_tweet(self.alex), 'a2')
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(len(response.data['comments']), 2)
        self.assertEqual(response.data['comments'][0]['content'], 'b1')
        self.assertEqual(response.data['comments'][1]['content'], 'a1')

        # try filter using both user_id and tweet_id, only tweet_id will be used to filter
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'user_id': self.bob.id,
        })
        self.assertEqual(len(response.data['comments']), 2)

    def test_comments_count(self):
        # test tweet detail api
        tweet = self.create_tweet(self.bob)
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.alex_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['comments_count'], 0)

        # test tweet list api
        self.create_comment(self.bob, tweet)
        response = self.alex_client.get(TWEET_LIST_API, {'user_id': self.bob.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['tweets'][0]['comments_count'], 1)

        # test newsfeeds list api
        self.create_comment(self.alex, tweet)
        self.create_newsfeed(self.alex, tweet)
        response = self.alex_client.get(NEWSFEED_LIST_API)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['newsfeeds'][0]['tweet']['comments_count'], 2)
