from testing.testcases import TestCase


class CommentModelTests(TestCase):
    def setUp(self):
        self.clear_cache()
        self.bob = self.create_user('bob')
        self.tweet = self.create_tweet(self.bob)
        self.comment = self.create_comment(self.bob, self.tweet)

    def test_comment(self):
        self.assertNotEqual(self.comment.__str__(), None)

    def test_like_set(self):
        self.create_like(self.bob, self.comment)
        self.assertEqual(self.comment.like_set.count(), 1)

        self.create_like(self.bob, self.comment)
        self.assertEqual(self.comment.like_set.count(), 1)

        alex = self.create_user('alex')
        self.create_like(alex, self.comment)
        self.assertEqual(self.comment.like_set.count(), 2)
