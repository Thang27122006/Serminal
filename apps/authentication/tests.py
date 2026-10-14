from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status


class AuthenticationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/auth/register/'
        self.login_url = '/api/v1/auth/login/'
        self.me_url = '/api/v1/auth/me/'

    def test_register_user_success(self):
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
        self.assertIn('token', response.data['data'])
        self.assertEqual(response.data['data']['user']['username'], 'testuser')

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

    def test_login_user_success(self):
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
        self.assertIn('token', response.data['data'])

    def test_login_invalid_credentials_fails(self):
        response = self.client.post(self.login_url, {
            'username': 'nonexistent',
            'password': 'WrongPassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])

    def test_me_endpoint_requires_auth(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_with_auth_success(self):
        user = User.objects.create_user(username='meuser', email='me@example.com', password='Password123')
        self.client.force_authenticate(user=user)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['username'], 'meuser')
