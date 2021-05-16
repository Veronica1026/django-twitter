from newsfeeds.models import NewsFeed
from friendships.models import Friendship
from rest_framework.test import APIClient
from testing.testcases import TestCase


NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEET_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'


class NewsFeedApiTests(TestCase):

    def setUp(self):
        self.bob = self.create_user('bob')
        self.bob_client = APIClient()
        self.bob_client.force_authenticate(self.bob)

        self.alex = self.create_user('alex')
        self.alex_client = APIClient()
        self.alex_client.force_authenticate(self.alex)

    def test_list(self):
        # need to login to see newsfeeds
        response = self.anonymous_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 403)

        # need to use get
        response = self.bob_client.post(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 405)

        # nothing at the beginning
        response = self.bob_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['newsfeeds']), 0)

        # one can see his own tweet
        self.bob_client.post(POST_TWEET_URL, {
            'content': 'hello I am bob'
        })
        response = self.bob_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['newsfeeds']), 1)

        # one can see other's tweets after following them
        self.bob_client.post(FOLLOW_URL.format(self.alex.id))
        response = self.alex_client.post(POST_TWEET_URL, {
            'content': 'hi Twitter!'
        })
        posted_tweet_id = response.data['id']
        response = self.bob_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['newsfeeds']), 2)
        self.assertEqual(response.data['newsfeeds'][0]['tweet']['id'], posted_tweet_id)
