from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status


class AuthenticationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/auth/register/'
        self.login_url = '/api/v1/auth/login/'
        self.refresh_url = '/api/v1/auth/token/refresh/'
        self.logout_url = '/api/v1/auth/logout/'
        self.me_url = '/api/v1/auth/me/'

    def test_register_user_success_with_jwt(self):
        payload = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "SecurePassword123@",
            "first_name": "Test",
            "last_name": "User"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])
        self.assertEqual(response.data['data']['user']['username'], 'testuser')
        # Đảm bảo không lộ password hash
        self.assertNotIn('password', response.data['data']['user'])

    def test_register_duplicate_username_fails(self):
        User.objects.create_user(username='existinguser', email='a@example.com', password='Password123')
        payload = {
            "username": "existinguser",
            "email": "b@example.com",
            "password": "Password123"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['error']['code'], 'VALIDATION_ERROR')

    def test_register_duplicate_email_fails(self):
        User.objects.create_user(username='user_one', email='common@example.com', password='Password123')
        payload = {
            "username": "user_two",
            "email": "common@example.com",
            "password": "Password123"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_register_short_password_fails(self):
        payload = {
            "username": "shortpwduser",
            "email": "short@example.com",
            "password": "123"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_login_user_success_with_jwt(self):
        User.objects.create_user(
            username='loginuser',
            email='loginuser@example.com',
            password='MyPassword123'
        )
        response = self.client.post(self.login_url, {
            'username': 'loginuser',
            'password': 'MyPassword123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])

    def test_login_invalid_password_fails(self):
        User.objects.create_user(username='targetuser', email='target@example.com', password='RealPassword123')
        response = self.client.post(self.login_url, {
            'username': 'targetuser',
            'password': 'WrongPassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])

    def test_jwt_token_refresh_workflow(self):
        User.objects.create_user(username='jwtuser', email='jwt@example.com', password='Password123')
        login_res = self.client.post(self.login_url, {'username': 'jwtuser', 'password': 'Password123'}, format='json')
        refresh_token = login_res.data['data']['refresh']

        refresh_res = self.client.post(self.refresh_url, {'refresh': refresh_token}, format='json')
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertTrue(refresh_res.data['success'])
        self.assertIn('access', refresh_res.data['data'])

    def test_jwt_token_refresh_invalid_token_fails(self):
        refresh_res = self.client.post(self.refresh_url, {'refresh': 'invalid.token.here'}, format='json')
        self.assertEqual(refresh_res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(refresh_res.data['success'])

    def test_logout_blacklists_refresh_token(self):
        user = User.objects.create_user(username='logoutuser', email='logout@example.com', password='Password123')
        login_res = self.client.post(self.login_url, {'username': 'logoutuser', 'password': 'Password123'}, format='json')
        access_token = login_res.data['data']['access']
        refresh_token = login_res.data['data']['refresh']

        # Đăng xuất gửi kèm refresh token
        logout_res = self.client.post(
            self.logout_url,
            {'refresh': refresh_token},
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            format='json'
        )
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)
        self.assertTrue(logout_res.data['success'])

        # Thử refresh bằng token đã bị blacklist -> phải bị chặn
        refresh_again_res = self.client.post(self.refresh_url, {'refresh': refresh_token}, format='json')
        self.assertEqual(refresh_again_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_requires_auth(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_with_jwt_bearer_token(self):
        User.objects.create_user(username='meuser', email='me@example.com', password='Password123')
        login_res = self.client.post(self.login_url, {'username': 'meuser', 'password': 'Password123'}, format='json')
        access_token = login_res.data['data']['access']

        response = self.client.get(self.me_url, HTTP_AUTHORIZATION=f"Bearer {access_token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['username'], 'meuser')

    def test_me_endpoint_with_invalid_jwt_bearer_token(self):
        response = self.client.get(self.me_url, HTTP_AUTHORIZATION="Bearer malformed.corrupted.token")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
