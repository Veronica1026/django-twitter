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
            follower = self.create_user('bob_follower{}'.format(i))
            Friendship.objects.create(from_user=follower, to_user=self.bob)
        for i in range(3):
            following = self.create_user('bob_following{}'.format(i))
            Friendship.objects.create(from_user=self.bob, to_user=following)

    def test_follow(self):
        url = FOLLOW_URL.format(self.bob.id)

        # need to login to follow others
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 403)
        # need to use post to follow
        response = self.alex_client.get(url)
        self.assertEqual(response.status_code, 405)
        # you cannot follow yourself
        response = self.bob_client.post(url)
        self.assertEqual(response.status_code, 400)
        # successful follow
        response = self.alex_client.post(url)
        self.assertEqual(response.status_code, 201)
        # self.assertEqual('user' in response.data, True)
        self.assertEqual('created_at' in response.data, True)
        self.assertEqual(response.data['user']['id'], self.bob.id)
        self.assertEqual(response.data['user']['username'], self.bob.username)

        # duplicate follow silent process
        response = self.alex_client.post(url)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['duplicate'], True)

        # follow back will create new records
        count = Friendship.objects.count()
        response = self.bob_client.post(FOLLOW_URL.format(self.alex.id))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Friendship.objects.count(), count + 1)

    def test_unfollow(self):
        url = UNFOLLOW_URL.format(self.bob.id)

        # need to login to unfollow others
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 403)
        # need to use post to unfollow
        response = self.alex_client.get(url)
        self.assertEqual(response.status_code, 405)
        # you cannot unfollow yourself
        response = self.bob_client.post(url)
        self.assertEqual(response.status_code, 400)
        # successful unfollow
        Friendship.objects.create(from_user=self.alex, to_user=self.bob)
        count = Friendship.objects.count()
        response = self.alex_client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted'], 1)
        self.assertEqual(Friendship.objects.count(), count - 1)
        # unfollow a person that you haven't followed, silent process
        count = Friendship.objects.count()
        response = self.alex_client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted'], 0)
        self.assertEqual(Friendship.objects.count(), count)

    def test_following(self):
        url = FOLLOWINGS_URL.format(self.bob.id)
        # post is not allowed
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 405)
        # get is ok
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['followings']), 3)
        # ensure sorted by timestamp desc
        ts0 = response.data['followings'][0]['created_at']
        ts1 = response.data['followings'][1]['created_at']
        ts2 = response.data['followings'][2]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(ts1 > ts2, True)

        self.assertEqual(
            response.data['followings'][0]['user']['username'],
            'bob_following2'
        )
        self.assertEqual(
            response.data['followings'][1]['user']['username'],
            'bob_following1'
        )
        self.assertEqual(
            response.data['followings'][2]['user']['username'],
            'bob_following0'
        )

    def test_follower(self):
        url = FOLLOWERS_URL.format(self.bob.id)
        # post is not allowed
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 405)

        # get is ok
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['followers']), 2)
        # sorted by time desc
        ts0 = response.data['followers'][0]['created_at']
        ts1 = response.data['followers'][1]['created_at']
        self.assertEqual(ts0 > ts1, True)

        self.assertEqual(
            response.data['followers'][0]['user']['username'],
            'bob_follower1'
        )

        self.assertEqual(
            response.data['followers'][1]['user']['username'],
            'bob_follower0'
        )

