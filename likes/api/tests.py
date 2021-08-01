from rest_framework.test import APIClient
from testing.testcases import TestCase

COMMENT_LIST_API = '/api/comments/'
LIKE_BASE_URL = '/api/likes/'
LIKE_CANCEL_URL = '/api/likes/cancel/'
NEWSFEED_LIST_API = '/api/newsfeeds/'
TWEET_DETAIL_API = '/api/tweets/{}/'
TWEET_LIST_API = '/api/tweets/'


class LikeApiTests(TestCase):
    def setUp(self):
        self.clear_cache()
        self.bob, self.bob_client = self.create_user_and_client('bob')
        self.alex, self.alex_client = self.create_user_and_client('alex')

    def test_tweet_likes(self):
        tweet = self.create_tweet(self.bob)
        data = {'content_type': 'tweet', 'object_id': tweet.id}

        # anonymous is forbidden
        response = self.anonymous_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 403)

        # get is not allowed
        response = self.bob_client.get(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 405)

        # invalid content type
        response = self.bob_client.post(LIKE_BASE_URL, {
            'content_type': 'twitter',
            'object_id': tweet.id,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('content_type' in response.data['errors'], True)

        # invalid object id
        response = self.bob_client.post(LIKE_BASE_URL, {
            'content_type': 'tweet',
            'object_id': 0,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('object_id' in response.data['errors'], True)

        # post success
        response = self.bob_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(tweet.like_set.count(), 1)

        # duplicate likes will not work
        self.bob_client.post(LIKE_BASE_URL, data)
        self.assertEqual(tweet.like_set.count(), 1)
        self.alex_client.post(LIKE_BASE_URL, data)
        self.assertEqual(tweet.like_set.count(), 2)

    def test_comment_likes(self):
        tweet = self.create_tweet(self.bob)
        comment = self.create_comment(self.bob, tweet)
        data = {'content_type': 'comment', 'object_id': comment.id}

        # anonymous is not allowed
        response = self.anonymous_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 403)

        # get is not allowed
        response = self.bob_client.get(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 405)

        # wrong content type
        response = self.bob_client.post(LIKE_BASE_URL, {
            'content_type': 'comet',
            'object_id': comment.id,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('content_type' in response.data['errors'], True)

        # wrong object_id
        response = self.bob_client.post(LIKE_BASE_URL, {
            'content_type': 'comment',
            'object_id': -1,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('object_id' in response.data['errors'], True)

        # post success
        response = self.bob_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(comment.like_set.count(), 1)

        # duplicate likes
        response = self.bob_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(comment.like_set.count(), 1)
        self.alex_client.post(LIKE_BASE_URL, data)
        self.assertEqual(comment.like_set.count(), 2)


    def test_cancel(self):
        tweet = self.create_tweet(self.bob)
        comment = self.create_comment(self.alex, tweet)
        like_tweet_data = {'content_type': 'tweet', 'object_id': tweet.id}
        like_comment_data = {'content_type': 'comment', 'object_id': comment.id}
        self.bob_client.post(LIKE_BASE_URL, like_comment_data)
        self.alex_client.post(LIKE_BASE_URL, like_tweet_data)
        self.assertEqual(tweet.like_set.count(), 1)
        self.assertEqual(comment.like_set.count(), 1)

        # login required
        response = self.anonymous_client.post(LIKE_CANCEL_URL, like_comment_data)
        self.assertEqual(response.status_code, 403)

        # get is not allowed
        response = self.bob_client.get(LIKE_CANCEL_URL, like_comment_data)
        self.assertEqual(response.status_code, 405)

        # wrong content_type
        response = self.bob_client.post(LIKE_CANCEL_URL, {
            'content_type': 'comet',
            'object_id': comment.id,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('content_type' in response.data['errors'], True)

        # wrong object_id
        response = self.bob_client.post(LIKE_CANCEL_URL, {
            'content_type': 'comment',
            'object_id': 0,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('object_id' in response.data['errors'], True)

        # bob has not liked the tweet before
        response = self.bob_client.post(LIKE_CANCEL_URL, like_tweet_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['rows_deleted'], 0)
        self.assertEqual(tweet.like_set.count(), 1)
        self.assertEqual(comment.like_set.count(), 1)

        # alex has not liked the comment before
        response = self.alex_client.post(LIKE_CANCEL_URL, like_comment_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['rows_deleted'], 0)
        self.assertEqual(tweet.like_set.count(), 1)
        self.assertEqual(comment.like_set.count(), 1)

        # bob cancels his like of the comment
        response = self.bob_client.post(LIKE_CANCEL_URL, like_comment_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['rows_deleted'], 1)
        self.assertEqual(tweet.like_set.count(), 1)
        self.assertEqual(comment.like_set.count(), 0)

        # alex cancels her like of the tweet
        response = self.alex_client.post(LIKE_CANCEL_URL, like_tweet_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['rows_deleted'], 1)
        self.assertEqual(tweet.like_set.count(), 0)
        self.assertEqual(comment.like_set.count(), 0)

    def test_like_in_comments_api(self):
        tweet = self.create_tweet(self.bob)
        comment = self.create_comment(self.bob, tweet)

        # test anonymous user
        response = self.anonymous_client.get(COMMENT_LIST_API, {'tweet_id': tweet.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['comments'][0]['has_liked'], False)
        self.assertEqual(response.data['comments'][0]['likes_count'], 0)

        # test comments list api
        response = self.alex_client.get(COMMENT_LIST_API, {'tweet_id': tweet.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['comments'][0]['has_liked'], False)
        self.assertEqual(response.data['comments'][0]['likes_count'], 0)
        self.create_like(self.alex, comment)
        response = self.alex_client.get(COMMENT_LIST_API, {'tweet_id': tweet.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['comments'][0]['has_liked'], True)
        self.assertEqual(response.data['comments'][0]['likes_count'], 1)

        # test tweet detail api
        self.create_like(self.bob, comment)
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.alex_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['comments'][0]['has_liked'], True)
        self.assertEqual(response.data['comments'][0]['likes_count'], 2)
        self.alex_client.post(LIKE_CANCEL_URL,{
            'content_type': 'comment',
            'object_id': comment.id,
            }
        )
        response = self.alex_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['comments'][0]['has_liked'], False)
        self.assertEqual(response.data['comments'][0]['likes_count'], 1)

    def test_like_in_tweets_api(self):
        tweet = self.create_tweet(self.bob)

        # test tweet detail api
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.alex_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['has_liked'], False)
        self.assertEqual(response.data['likes_count'], 0)
        self.create_like(self.alex, tweet)
        response = self.alex_client.get(url)
        self.assertEqual(response.data['has_liked'], True)
        self.assertEqual(response.data['likes_count'], 1)

        # test tweet list api
        response = self.alex_client.get(TWEET_LIST_API, {'user_id': self.bob.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['has_liked'], True)
        self.assertEqual(response.data['results'][0]['likes_count'], 1)

        # test newsfeeds list api
        self.create_like(self.bob, tweet)
        self.create_newsfeed(self.alex, tweet)
        response = self.alex_client.get(NEWSFEED_LIST_API)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['tweet']['has_liked'], True)
        self.assertEqual(response.data['results'][0]['tweet']['likes_count'], 2)

        # test tweet likes details
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.alex_client.get(url)
        self.assertEqual(len(response.data['likes']), 2)
        self.assertEqual(response.data['likes'][0]['user']['id'], self.bob.id)
        self.assertEqual(response.data['likes'][1]['user']['id'], self.alex.id)

    def test_likes_count(self):
        tweet = self.create_tweet(self.bob)
        data = {'content_type': 'tweet', 'object_id': tweet.id}
        self.bob_client.post(LIKE_BASE_URL, data)

        tweet_url = TWEET_DETAIL_API.format(tweet.id)
        response = self.bob_client.get(tweet_url)
        self.assertEqual(response.data['likes_count'], 1)
        tweet.refresh_from_db()
        self.assertEqual(tweet.likes_count, 1)

        # cancel likes
        self.bob_client.post(LIKE_BASE_URL + 'cancel/', data)
        tweet.refresh_from_db()
        self.assertEqual(tweet.likes_count, 0)
        response = self.bob_client.get(tweet_url)
        self.assertEqual(response.data['likes_count'], 0)



