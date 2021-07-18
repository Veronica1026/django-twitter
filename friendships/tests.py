from friendships.models import Friendship
from friendships.services import FriendshipService
from testing.testcases import TestCase


class FriendshipServiceTests(TestCase):
    def setUp(self):
        self.clear_cache()
        self.bob = self.create_user('bob')
        self.alex = self.create_user('alex')

    def test_get_followings(self):
        user1 = self.create_user('user1')
        user2 = self.create_user('user2')
        for to_user in [user1, user2, self.alex]:
            Friendship.objects.create(from_user=self.bob, to_user=to_user)
        FriendshipService.invalidate_following_cache(self.bob.id)
        user_id_set = FriendshipService.get_following_user_id_set(self.bob.id)
        self.assertEqual(user_id_set, {user1.id, user2.id, self.alex.id})

        Friendship.objects.filter(from_user=self.bob, to_user=self.alex).delete()
        FriendshipService.invalidate_following_cache(self.bob.id)
        user_id_set = FriendshipService.get_following_user_id_set(self.bob.id)
        self.assertEqual(user_id_set, {user1.id, user2.id})
