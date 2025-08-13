import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from knox.models import AuthToken
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import RoleApplication, RoleForm, FormField, RoleApplicationFile

User = get_user_model()

class AuthAPITests(APITestCase):

    def setUp(self):
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:knox_login')
        self.user_url = reverse('accounts:user')
        self.logout_url = reverse('accounts:knox_logout')

        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword',
            'password2': 'testpassword',
            'phone_number': '1234567890'
        }
        self.user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpassword2'
        )
        cache.clear()

    def test_register_user(self):
        """
        Ensure we can create a new user and get a token.
        """
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(User.objects.get(username='testuser').email, 'test@example.com')
        self.assertIn('token', response.data)

    def test_login_user(self):
        """
        Ensure a registered user can login and get a token.
        """
        data = {'username': 'testuser2', 'password': 'testpassword2'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_get_user_data(self):
        """
        Ensure an authenticated user can get their own data.
        """
        token = AuthToken.objects.create(self.user)[1]
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        response = self.client.get(self.user_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user.username)

    def test_logout_user(self):
        """
        Ensure an authenticated user can logout.
        """
        token = AuthToken.objects.create(self.user)[1]
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify the token is deleted
        self.assertEqual(AuthToken.objects.count(), 0)

    def test_register_duplicate_email(self):
        """
        Ensure we cannot register with a duplicate email.
        """
        # Create a user with a specific email
        User.objects.create_user(username='user1', email='duplicate@example.com', password='password123')
        # Try to register another user with the same email
        user_data = self.user_data.copy()
        user_data['email'] = 'duplicate@example.com'
        response = self.client.post(self.register_url, user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_email_normalization(self):
        """
        Ensure email is normalized to lowercase.
        """
        user_data = self.user_data.copy()
        user_data['email'] = 'NORMALIZE@EXAMPLE.COM'
        response = self.client.post(self.register_url, user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.get(username='testuser').email, 'normalize@example.com')

    def test_register_rate_limit(self):
        """
        Ensure registration endpoint is rate limited.
        """
        # The rate is 5/min. We will make 6 requests.
        for i in range(5):
            user_data = self.user_data.copy()
            user_data['username'] = f"ratelimit{i}"
            user_data['email'] = f"ratelimit{i}@example.com"
            user_data['phone_number'] = f"123456788{i}"
            response = self.client.post(self.register_url, user_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # The 6th request should be throttled
        user_data = self.user_data.copy()
        user_data['username'] = "ratelimit6"
        user_data['email'] = "ratelimit6@example.com"
        user_data['phone_number'] = "1234567886"
        response = self.client.post(self.register_url, user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class RoleApplicationAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        cls.role_form = RoleForm.objects.create(name='Driver Application', role='driver')
        FormField.objects.create(role_form=cls.role_form, label='License Number', field_type='text')
        FormField.objects.create(role_form=cls.role_form, label='License Document', field_type='file')

    def setUp(self):
        self.apply_url = reverse('accounts:role_apply')
        self.client.force_authenticate(user=self.user)

    def test_apply_for_role(self):
        """
        Ensure an authenticated user can apply for a role.
        """
        document = SimpleUploadedFile("license.txt", b"file_content", content_type="text/plain")
        form_data = {
            'License Number': '12345',
        }
        data = {
            'role_form': self.role_form.id,
            'form_data': json.dumps(form_data),
            'License Document': document
        }
        response = self.client.post(self.apply_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RoleApplication.objects.count(), 1)
        application = RoleApplication.objects.first()
        self.assertEqual(application.user, self.user)
        self.assertEqual(application.role_form, self.role_form)
        self.assertEqual(application.status, 'pending')
        self.assertEqual(application.files.count(), 1)


class RoleApplicationAdminAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        cls.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        cls.role_form = RoleForm.objects.create(name='Driver Application', role='driver')
        cls.application = RoleApplication.objects.create(
            user=cls.user,
            role_form=cls.role_form,
            form_data={'License Number': '12345'}
        )

    def setUp(self):
        self.list_url = reverse('accounts:admin_roles-list')
        self.detail_url = reverse('accounts:admin_roles-detail', kwargs={'pk': self.application.pk})

    def test_list_applications_as_admin(self):
        """
        Ensure admin can list applications.
        """
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_applications_as_user(self):
        """
        Ensure non-admin cannot list applications.
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_approve_application_as_admin(self):
        """
        Ensure admin can approve an application.
        """
        self.client.force_authenticate(user=self.admin_user)
        data = {'status': 'approved'}
        response = self.client.patch(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'approved')
        self.user.refresh_from_db()
        self.assertEqual(self.user.user_type, 'driver')
        self.assertTrue(self.user.is_role_verified)

    def test_reject_application_as_admin(self):
        """
        Ensure admin can reject an application.
        """
        self.client.force_authenticate(user=self.admin_user)
        data = {'status': 'rejected'}
        response = self.client.patch(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'rejected')
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.user_type, 'driver')
        self.assertFalse(self.user.is_role_verified)
