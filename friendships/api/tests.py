from friendships.services import FriendshipService
from rest_framework.test import APIClient
from testing.testcases import TestCase
from utils.paginations import EndlessPagination


FOLLOW_URL = '/api/friendships/{}/follow/'
UNFOLLOW_URL = '/api/friendships/{}/unfollow/'
FOLLOWERS_URL = '/api/friendships/{}/followers/'
FOLLOWINGS_URL = '/api/friendships/{}/followings/'


class FriendshipApiTests(TestCase):

    def setUp(self):
        super(FriendshipApiTests, self).setUp()
        self.bob = self.create_user('bob')
        self.bob_client = APIClient()
        self.bob_client.force_authenticate(self.bob)

        self.alex = self.create_user('alex')
        self.alex_client = APIClient()
        self.alex_client.force_authenticate(self.alex)

        #create followings and followers for bob
        for i in range(2):
            follower = self.create_user('alex_follower{}'.format(i))
            self.create_friendship(from_user=follower, to_user=self.alex)
        for i in range(3):
            following = self.create_user('alex_following{}'.format(i))
            self.create_friendship(from_user=self.alex, to_user=following)

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
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['duplicate'], True)

        # follow back will create new records
        before_count = FriendshipService.get_following_count(self.alex.id)
        response = self.alex_client.post(FOLLOW_URL.format(self.bob.id))
        self.assertEqual(response.status_code, 201)
        after_count = FriendshipService.get_following_count(self.alex.id)
        self.assertEqual(after_count, before_count + 1)

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
        self.create_friendship(from_user=self.bob, to_user=self.alex)
        before_count = FriendshipService.get_following_count(self.bob.id)
        response = self.bob_client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted'], 1)
        after_count = FriendshipService.get_following_count(self.bob.id)
        self.assertEqual(after_count, before_count - 1)
        # unfollow a person that you haven't followed, silent process
        before_count = FriendshipService.get_following_count(self.alex.id)
        response = self.bob_client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted'], 0)
        after_count = FriendshipService.get_following_count(self.alex.id)
        self.assertEqual(before_count, after_count)

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
        page_size = EndlessPagination.page_size
        friendships = []
        for i in range(page_size * 2):
            follower = self.create_user('bob_follower_{}'.format(i))
            friendship = self.create_friendship(from_user=follower, to_user=self.bob)
            friendships.append(friendship)
            if follower.id % 2 == 0:
                self.create_friendship(from_user=self.alex, to_user=follower)

        url = FOLLOWERS_URL.format(self.bob.id)
        self._paginate_until_the_end(url, 2, friendships)

        # anonymous user has not followed anyone
        response = self.anonymous_client.get(url)
        for results in response.data['results']:
            self.assertEqual(results['has_followed'], False)

        # alex has followed users with even id
        response = self.alex_client.get(url)
        for result in response.data['results']:
            has_followed = (result['user']['id'] % 2 == 0)
            self.assertEqual(result['has_followed'], has_followed)

    def test_following_pagination(self):
        page_size = EndlessPagination.page_size
        friendships = []
        for i in range(page_size * 2):
            following = self.create_user('bob_following_{}'.format(i))
            friendship = self.create_friendship(from_user=self.bob, to_user=following)
            friendships.append(friendship)
            if following.id % 2 == 0:
                self.create_friendship(from_user=self.alex, to_user=following)

        url = FOLLOWINGS_URL.format(self.bob.id)
        self._paginate_until_the_end(url, 2, friendships)

        # anonymous user hasn't followed anyone yet
        response = self.anonymous_client.get(url)
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], False)

        # alex has followed user with even id
        response = self.alex_client.get(url)
        for result in response.data['results']:
            has_followed = (result['user']['id'] % 2 == 0)
            self.assertEqual(result['has_followed'], has_followed)

        # bob has followed all the users that he has followed
        response = self.bob_client.get(url)
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], True)

        # test pull new friendships
        last_created_at = friendships[-1].created_at
        response = self.bob_client.get(url, {'created_at__gt': last_created_at})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

        new_friends = [self.create_user('super_star{}'.format(i)) for i in range(3)]
        new_friendships = []
        for friend in new_friends:
            new_friendships.append(self.create_friendship(from_user=self.bob, to_user=friend))
        response = self.bob_client.get(url, {'created_at__gt': last_created_at})
        self.assertEqual(len(response.data['results']), 3)
        for result, friendship in zip(response.data['results'], reversed(new_friendships)):
            self.assertEqual(result['created_at'], friendship.created_at)

    def _paginate_until_the_end(self, url, expect_pages, friendships):
        results, pages = [], 0
        response = self.anonymous_client.get(url)
        results.extend(response.data['results'])
        pages += 1
        while response.data['has_next_page']:
            self.assertEqual(response.status_code, 200)
            last_item = response.data['results'][-1]
            response = self.anonymous_client.get(url, {
                'created_at__lt': last_item['created_at'],
            })
            results.extend(response.data['results'])
            pages += 1

        self.assertEqual(len(results), len(friendships))
        self.assertEqual(pages, expect_pages)
        # friendship is in ascending order, result is in descending order
        for result, friendship in zip(results, friendships[::-1]):
            self.assertEqual(result['created_at'], friendship.created_at)
