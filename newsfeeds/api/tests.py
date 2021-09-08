from django.conf import settings
from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService
from rest_framework.test import APIClient
from testing.testcases import TestCase
from utils.paginations import EndlessPagination


NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEET_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'


class NewsFeedApiTests(TestCase):

    def setUp(self):
        super(NewsFeedApiTests, self).setUp()
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

    def test_user_cache(self):
        profile = self.alex.profile
        profile.nickname = 'lex'
        profile.save()

        self.assertEqual(self.bob.username, 'bob')
        self.create_newsfeed(self.alex, self.create_tweet(self.bob))
        self.create_newsfeed(self.alex, self.create_tweet(self.alex))

        response = self.alex_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'alex')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'lex')
        self.assertEqual(results[1]['tweet']['user']['username'], 'bob')

        self.bob.username = 'bobbystar'
        self.bob.save()
        profile.nickname = 'lexgogo'
        profile.save()

        response = self.alex_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'alex')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'lexgogo')
        self.assertEqual(results[1]['tweet']['user']['username'], 'bobbystar')

    def test_tweet_cache(self):
        tweet = self.create_tweet(self.bob, 'content1')
        self.create_newsfeed(self.alex, tweet)
        response = self.alex_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'bob')
        self.assertEqual(results[0]['tweet']['content'], 'content1')

        # update username
        self.bob.username = 'bobbybee'
        self.bob.save()
        response = self.alex_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'bobbybee')

        # update content
        tweet.content = 'content2'
        tweet.save()
        response = self.alex_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['content'], 'content2')

    def _paginate_to_get_newsfeeds(self, client):
        # paginate until the end
        response = client.get(NEWSFEEDS_URL)
        results = response.data['results']
        while response.data['has_next_page']:
            created_at__lt = response.data['results'][-1]['created_at']
            response = client.get(NEWSFEEDS_URL, {'created_at__lt': created_at__lt})
            results.extend(response.data['results'])
        return results

    def test_redis_list_limit(self):
        list_limit = settings.REDIS_LIST_LENGTH_LIMIT
        page_size = 20
        users = [self.create_user('user{}'.format(i)) for i in range(5)]
        newsfeeds = []
        for i in range(list_limit + page_size):
            tweet = self.create_tweet(user=users[i % 5], content='feed{}'.format(i))
            feed = self.create_newsfeed(self.bob, tweet)
            newsfeeds.append(feed)
        newsfeeds = newsfeeds[::-1]

        # only cached list_limit objects
        cached_newsfeeds = NewsFeedService.get_cached_newsfeeds(self.bob.id)
        self.assertEqual(len(cached_newsfeeds), list_limit)
        queryset = NewsFeed.objects.filter(user=self.bob)
        self.assertEqual(queryset.count(), list_limit + page_size)

        results = self._paginate_to_get_newsfeeds(self.bob_client)
        self.assertEqual(len(results), list_limit + page_size)
        for i in range(list_limit + page_size):
            self.assertEqual(results[i]['id'], newsfeeds[i].id)

        # a followed user create a new tweet
        self.create_friendship(self.bob, self.alex)
        new_tweet = self.create_tweet(self.alex, 'a new tweet')
        NewsFeedService.fanout_to_followers(new_tweet)

        def _test_newsfeeds_after_new_feed_pushed():
            results = self._paginate_to_get_newsfeeds(self.bob_client)
            self.assertEqual(len(results), list_limit + page_size + 1)
            self.assertEqual(results[0]['tweet']['id'], new_tweet.id)
            for i in range(list_limit + page_size):
                self.assertEqual(results[i + 1]['id'], newsfeeds[i].id)

        _test_newsfeeds_after_new_feed_pushed()

        # cache expired
        self.clear_cache()
        _test_newsfeeds_after_new_feed_pushed()






