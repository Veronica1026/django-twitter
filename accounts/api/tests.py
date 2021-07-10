from accounts.models import UserProfile
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from testing.testcases import TestCase


LOGIN_URL = '/api/accounts/login/'
LOGOUT_URL = '/api/accounts/logout/'
SIGNUP_URL = '/api/accounts/signup/'
LOGIN_STATUS_URL = '/api/accounts/login_status/'
USER_PROFILE_DETAIL_URL = '/api/profiles/{}/'


class AccountApiTests(TestCase):

    def setUp(self):
        # will be executed when each test function gets executed
        self.client = APIClient()
        self.user = self.create_user(
            username='admin',
            email='admin@jiuzhang.com',
            password='correct password',
        )


    def test_login(self):

        # test that we need to use post, not get
        response = self.client.get(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })

        # 405 = METHOD_NOT_ALLOWED
        self.assertEqual(response.status_code, 405)

        # test wrong password
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'wrong password',
        })
        self.assertEqual(response.status_code, 400)

        # validate we are not logged in yet
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

        # use the correct password
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data['user'], None)
        self.assertEqual(response.data['user']['id'], self.user.id)

        # validate we have logged in
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

    def test_logout(self):
        self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })

        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

        response = self.client.get(LOGOUT_URL)
        self.assertEqual(response.status_code, 405)

        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

    def test_signup(self):
        data = {
            'username': 'someone',
            'email': 'someone@jiuzhang.com',
            'password': 'any password',
        }

        # test get request fails
        response = self.client.get(SIGNUP_URL, data)
        self.assertEqual(response.status_code, 405)

        # test wrong email
        response = self.client.post(SIGNUP_URL, {
            'username': 'someone',
            'email': 'not a correct email',
            'password': 'any password',
        })
        self.assertEqual(response.status_code, 400)

        # test password too short
        response = self.client.post(SIGNUP_URL, {
            'username': 'someone',
            'email': 'someone@jiuzhang.com',
            'password': '123',
        })
        self.assertEqual(response.status_code, 400)

        # test username too long
        response = self.client.post(SIGNUP_URL, {
            'username': 'username is tooooooooooooooooo loooooooong',
            'email': 'someone@jiuzhang.com',
            'password': 'any password',
        })
        self.assertEqual(response.status_code, 400)

        # successful signup
        response = self.client.post(SIGNUP_URL, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user']['username'], 'someone')

        # validate that user profile is created
        created_user_id = response.data['user']['id']
        profile = UserProfile.objects.filter(user_id=created_user_id).first()
        self.assertNotEqual(profile, None)

        # validate user has logged in
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)


class UserProfileAPITests(TestCase):

    def test_update(self):
        bob, bob_client = self.create_user_and_client('bob')
        p = bob.profile
        p.nickname = 'old bobby'
        p.save()
        url = USER_PROFILE_DETAIL_URL.format(p.id)

        # anonymous user cannot update profile
        response = self.anonymous_client.put(url, {
            'nickname': 'new new new bob',
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['detail'], 'Authentication credentials were not provided.')
        p.refresh_from_db()
        self.assertEqual(p.nickname, 'old bobby')

        # test profile can only be updated by the owner
        _, alex_client = self.create_user_and_client('alex')
        response = alex_client.put(url, {
            'nickname': 'the brand_new bob!!',
        })
        self.assertEqual(response.status_code, 403)
        p.refresh_from_db()
        self.assertEqual(p.nickname, 'old bobby')
        self.assertEqual(response.data['detail'], 'You do not have permission to access this object')

        # update nickname by the owner
        response = bob_client.put(url, {
            'nickname': 'happy bob',
        })
        self.assertEqual(response.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.nickname, 'happy bob')

        # update avatar
        response = bob_client.put(url, {
            'avatar': SimpleUploadedFile(
                name='bob-photo.jpg',
                content=str.encode('a fake image'),
                content_type='image/jpeg',
            ),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual('bob-photo' in response.data['avatar'], True)
        p.refresh_from_db
        self.assertIsNotNone(p.avatar)

