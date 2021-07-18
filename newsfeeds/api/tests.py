from friendships.models import Friendship
from newsfeeds.models import NewsFeed
from rest_framework.test import APIClient
from testing.testcases import TestCase
from utils.paginations import EndlessPagination


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
        self.assertEqual(len(response.data['results']), 0)

        # one can see his own tweet
        self.bob_client.post(POST_TWEET_URL, {
            'content': 'hello I am bob'
        })
        response = self.bob_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 1)

        # one can see other's tweets after following them
        self.bob_client.post(FOLLOW_URL.format(self.alex.id))
        response = self.alex_client.post(POST_TWEET_URL, {
            'content': 'hi Twitter!'
        })
        posted_tweet_id = response.data['id']
        response = self.bob_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['tweet']['id'], posted_tweet_id)

    def test_pagination(self):
        page_size = EndlessPagination.page_size
        followed_user = self.create_user('followee')
        newsfeeds = []
        for i in range(page_size * 2):
            tweet = self.create_tweet(followed_user)
            newsfeed = self.create_newsfeed(user=self.bob, tweet=tweet)
            newsfeeds.append(newsfeed)

        # sort by created_at desc
        newsfeeds = newsfeeds[::-1]

        # pull the first page
        response = self.bob_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.data['has_next_page'], True)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['results'][0]['id'], newsfeeds[0].id)
        self.assertEqual(response.data['results'][1]['id'], newsfeeds[1].id)
        self.assertEqual(
            response.data['results'][page_size - 1]['id'],
            newsfeeds[page_size - 1].id
        )

        # pull the second page
        response = self.bob_client.get(NEWSFEEDS_URL, {
           'created_at__lt': newsfeeds[page_size - 1].created_at
        })
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['results'][0]['id'], newsfeeds[page_size].id)
        self.assertEqual(response.data['results'][1]['id'], newsfeeds[page_size + 1].id)
        self.assertEqual(
            response.data['results'][page_size - 1]['id'],
            newsfeeds[page_size * 2 - 1].id
        )

        # pull latest newsfeeds
        response = self.bob_client.get(NEWSFEEDS_URL, {
                'created_at__gt': newsfeeds[0].created_at,
            }
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 0)

        tweet = self.create_tweet(followed_user)
        new_newsfeed = self.create_newsfeed(user=self.bob, tweet=tweet)

        response = self.bob_client.get(NEWSFEEDS_URL, {
                'created_at__gt': newsfeeds[0].created_at,
            }
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], new_newsfeed.id)