from friendships.api.paginations import FriendshipPagination
from friendships.models import Friendship
from rest_framework.test import APIClient
from testing.testcases import TestCase


FOLLOW_URL = '/api/friendships/{}/follow/'
UNFOLLOW_URL = '/api/friendships/{}/unfollow/'
FOLLOWERS_URL = '/api/friendships/{}/followers/'
FOLLOWINGS_URL = '/api/friendships/{}/followings/'


class FriendshipApiTests(TestCase):

    def setUp(self):

        self.bob = self.create_user('bob')
        self.bob_client = APIClient()
        self.bob_client.force_authenticate(self.bob)

        self.alex = self.create_user('alex')
        self.alex_client = APIClient()
        self.alex_client.force_authenticate(self.alex)

        #create followings and followers for bob
        for i in range(2):
            follower = self.create_user('alex_follower{}'.format(i))
            Friendship.objects.create(from_user=follower, to_user=self.alex)
        for i in range(3):
            following = self.create_user('alex_following{}'.format(i))
            Friendship.objects.create(from_user=self.alex, to_user=following)

    def test_follow(self):
        url = FOLLOW_URL.format(self.alex.id)

        # need to login to follow others
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 403)
        # need to use post to follow
        response = self.bob_client.get(url)
        self.assertEqual(response.status_code, 405)
        # you cannot follow yourself
        response = self.alex_client.post(url)
        self.assertEqual(response.status_code, 400)
        # successful follow
        response = self.bob_client.post(url)
        self.assertEqual(response.status_code, 201)
        # self.assertEqual('user' in response.data, True)
        self.assertEqual('created_at' in response.data, True)
        self.assertEqual(response.data['user']['id'], self.alex.id)
        self.assertEqual(response.data['user']['username'], self.alex.username)

        # duplicate follow silent process
        response = self.bob_client.post(url)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['duplicate'], True)

        # follow back will create new records
        count = Friendship.objects.count()
        response = self.alex_client.post(FOLLOW_URL.format(self.bob.id))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Friendship.objects.count(), count + 1)

    def test_unfollow(self):
        url = UNFOLLOW_URL.format(self.alex.id)

        # need to login to unfollow others
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 403)
        # need to use post to unfollow
        response = self.bob_client.get(url)
        self.assertEqual(response.status_code, 405)
        # you cannot unfollow yourself
        response = self.alex_client.post(url)
        self.assertEqual(response.status_code, 400)
        # successful unfollow
        Friendship.objects.create(from_user=self.bob, to_user=self.alex)
        count = Friendship.objects.count()
        response = self.bob_client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted'], 1)
        self.assertEqual(Friendship.objects.count(), count - 1)
        # unfollow a person that you haven't followed, silent process
        count = Friendship.objects.count()
        response = self.bob_client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted'], 0)
        self.assertEqual(Friendship.objects.count(), count)

    def test_following(self):
        url = FOLLOWINGS_URL.format(self.alex.id)
        # post is not allowed
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 405)
        # get is ok
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)
        # ensure sorted by timestamp desc
        ts0 = response.data['results'][0]['created_at']
        ts1 = response.data['results'][1]['created_at']
        ts2 = response.data['results'][2]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(ts1 > ts2, True)

        self.assertEqual(
            response.data['results'][0]['user']['username'],
            'alex_following2'
        )
        self.assertEqual(
            response.data['results'][1]['user']['username'],
            'alex_following1'
        )
        self.assertEqual(
            response.data['results'][2]['user']['username'],
            'alex_following0'
        )

    def test_follower(self):
        url = FOLLOWERS_URL.format(self.alex.id)
        # post is not allowed
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 405)

        # get is ok
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)

        # sorted by time desc
        ts0 = response.data['results'][0]['created_at']
        ts1 = response.data['results'][1]['created_at']
        self.assertEqual(ts0 > ts1, True)

        self.assertEqual(
            response.data['results'][0]['user']['username'],
            'alex_follower1'
        )

        self.assertEqual(
            response.data['results'][1]['user']['username'],
            'alex_follower0'
        )

    def test_follower_pagination(self):
        max_page_size = FriendshipPagination.max_page_size
        page_size = FriendshipPagination.page_size
        for i in range(page_size * 2):
            follower = self.create_user('bob_follower_{}'.format(i))
            Friendship.objects.create(from_user=follower, to_user=self.bob)
            if follower.id % 2 == 0:
                Friendship.objects.create(from_user=self.alex, to_user=follower)

        url = FOLLOWERS_URL.format(self.bob.id)
        self._test_friendship_pagination(url, page_size, max_page_size)

        # anonymous user has not followed anyone
        response = self.anonymous_client.get(url, {'page': 1})
        for results in response.data['results']:
            self.assertEqual(results['has_followed'], False)

        # alex has followed users with even id
        response = self.alex_client.get(url, {'page': 1})
        for result in response.data['results']:
            has_followed = (result['user']['id'] % 2 == 0)
            self.assertEqual(result['has_followed'], has_followed)

    def test_following_pagination(self):
        max_page_size = FriendshipPagination.max_page_size
        page_size = FriendshipPagination.page_size
        for i in range(page_size * 2):
            following = self.create_user('bob_following_{}'.format(i))
            Friendship.objects.create(from_user=self.bob, to_user=following)
            if following.id % 2 == 0:
                Friendship.objects.create(from_user=self.alex, to_user=following)

        url = FOLLOWINGS_URL.format(self.bob.id)
        self._test_friendship_pagination(url, page_size, max_page_size)

        # anonymous user hasn't followed anyone yet
        response = self.anonymous_client.get(url, {'page': 1})
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], False)

        # alex has followed user with even id
        response = self.alex_client.get(url, {'page': 1})
        for result in response.data['results']:
            has_followed = (result['user']['id'] % 2 == 0)
            self.assertEqual(result['has_followed'], has_followed)

        # bob has followed all the users that he has followed
        response = self.bob_client.get(url, {'page': 1})
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], True)

    def _test_friendship_pagination(self, url, page_size, max_page_size):
        response = self.anonymous_client.get(url, {'page': 1})
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)

        response = self.anonymous_client.get(url, {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 2)
        self.assertEqual(response.data['has_next_page'], False)

        response = self.anonymous_client.get(url, {'page': 3})
        self.assertEqual(response.status_code, 404)

        # test user cannot customize page_size that exceeds max_page_size
        response= self.anonymous_client.get(url, {'page': 1, 'size': max_page_size + 1})
        self.assertEqual(len(response.data['results']), max_page_size)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)

        # test user cannot customize page_size within the limit of max_page_size
        response= self.anonymous_client.get(url, {'page': 1, 'size': 2})
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['total_pages'], page_size)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)
