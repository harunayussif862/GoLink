from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import connection
from knox.models import AuthToken
import pyotp
import base64
from django_otp.util import random_hex
from django_otp.plugins.otp_totp.models import TOTPDevice

User = get_user_model()

class ChangePasswordAPITests(APITransactionTestCase):

    def setUp(self):
        self.user_with_2fa = User.objects.create_user(
            username='user_2fa',
            email='2fa@example.com',
            password='oldpassword'
        )
        self.device = self._create_confirmed_device(self.user_with_2fa)

        self.user_no_2fa = User.objects.create_user(
            username='user_no_2fa',
            email='no2fa@example.com',
            password='oldpassword'
        )

        self.change_password_url = reverse('accounts:change_password')

    def _create_confirmed_device(self, user):
        device = TOTPDevice.objects.create(
            user=user,
            name="default",
            confirmed=True,
            key=random_hex()
        )
        connection.commit()
        return device

    def _get_valid_otp(self, device):
        secret_b32 = base64.b32encode(bytes.fromhex(device.key)).decode()
        return pyotp.TOTP(secret_b32).now()

    def test_change_password_success_with_2fa(self):
        self.client.force_authenticate(user=self.user_with_2fa)
        otp_code = self._get_valid_otp(self.device)
        data = {
            "old_password": "oldpassword",
            "new_password1": "a-very-strong-password-123!",
            "new_password2": "a-very-strong-password-123!",
            "otp_code": otp_code
        }
        response = self.client.post(self.change_password_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_with_2fa.refresh_from_db()
        self.assertTrue(self.user_with_2fa.check_password("a-very-strong-password-123!"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Your GoLink Password Was Changed", mail.outbox[0].subject)
        self.assertEqual(AuthToken.objects.filter(user=self.user_with_2fa).count(), 0)

    def test_change_password_success_no_2fa(self):
        self.client.force_authenticate(user=self.user_no_2fa)
        data = {
            "old_password": "oldpassword",
            "new_password1": "a-very-strong-password-123!",
            "new_password2": "a-very-strong-password-123!",
        }
        response = self.client.post(self.change_password_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_no_2fa.refresh_from_db()
        self.assertTrue(self.user_no_2fa.check_password("a-very-strong-password-123!"))
        self.assertEqual(len(mail.outbox), 1)

    def test_change_password_wrong_old_password(self):
        self.client.force_authenticate(user=self.user_with_2fa)
        otp_code = self._get_valid_otp(self.device)
        data = {
            "old_password": "wrongpassword",
            "new_password1": "newpassword",
            "new_password2": "newpassword",
            "otp_code": otp_code
        }
        response = self.client.post(self.change_password_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Incorrect old password", response.data['error'])

    def test_change_password_missing_otp(self):
        self.client.force_authenticate(user=self.user_with_2fa)
        data = {
            "old_password": "oldpassword",
            "new_password1": "newpassword",
            "new_password2": "newpassword",
        }
        response = self.client.post(self.change_password_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("OTP code is required", response.data['error'])

    def test_change_password_invalid_otp(self):
        self.client.force_authenticate(user=self.user_with_2fa)
        data = {
            "old_password": "oldpassword",
            "new_password1": "newpassword",
            "new_password2": "newpassword",
            "otp_code": "123456"
        }
        response = self.client.post(self.change_password_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid OTP code", response.data['error'])

    def test_change_password_rate_limit(self):
        self.client.force_authenticate(user=self.user_with_2fa)
        for i in range(5):
            data = {
                "old_password": "wrongpassword",
                "new_password1": "newpassword",
                "new_password2": "newpassword",
                "otp_code": "123456"
            }
            response = self.client.post(self.change_password_url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 6th attempt should be throttled
        response = self.client.post(self.change_password_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
