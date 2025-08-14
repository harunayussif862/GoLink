from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Wallet, Transaction
from .utils import handle_commission
from decimal import Decimal

User = get_user_model()

class WalletAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.client.force_authenticate(user=self.user)
        self.wallet = Wallet.objects.get(user=self.user)
        self.wallet_url = reverse('wallets:wallet')
        self.transactions_url = reverse('wallets:transactions')
        self.deposit_url = reverse('wallets:deposit')
        self.withdraw_url = reverse('wallets:withdraw')
        self.transfer_url = reverse('wallets:transfer')

    def test_wallet_creation(self):
        """
        Test that a wallet is automatically created for a new user.
        """
        self.assertIsNotNone(self.wallet)
        self.assertEqual(self.wallet.balance, 0)

    def test_get_wallet_details(self):
        """
        Ensure an authenticated user can get their wallet details.
        """
        response = self.client.get(self.wallet_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['wallet_id'], str(self.wallet.wallet_id))
        self.assertEqual(float(response.data['balance']), 0.00)

    def test_list_transactions(self):
        """
        Ensure an authenticated user can list their transactions.
        """
        Transaction.objects.create(wallet=self.wallet, transaction_type='deposit', amount=100, status='completed')
        Transaction.objects.create(wallet=self.wallet, transaction_type='withdrawal', amount=50, status='completed')

        response = self.client.get(self.transactions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['amount'], '50.00') # Ordered by -timestamp
        self.assertEqual(response.data[1]['amount'], '100.00')

    def test_deposit(self):
        """
        Ensure a user can deposit money into their wallet.
        """
        data = {'amount': '100.50'}
        response = self.client.post(self.deposit_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 100.50)
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(Transaction.objects.first().transaction_type, 'deposit')

    def test_withdraw(self):
        """
        Ensure a user can make a withdrawal request.
        """
        self.wallet.balance = 200
        self.wallet.save()
        data = {'amount': '50.25'}
        response = self.client.post(self.withdraw_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 200) # Balance should not change
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(Transaction.objects.first().status, 'pending')

    def test_withdraw_insufficient_balance(self):
        """
        Ensure a user cannot withdraw more than their balance.
        """
        data = {'amount': '100.00'}
        response = self.client.post(self.withdraw_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer(self):
        """
        Ensure a user can transfer money to another wallet.
        """
        recipient_user = User.objects.create_user(username='recipient', email='recipient@example.com', password='password')
        recipient_wallet = Wallet.objects.get(user=recipient_user)

        self.wallet.balance = 300
        self.wallet.save()

        data = {
            'recipient_wallet_id': str(recipient_wallet.wallet_id),
            'amount': '100.00'
        }
        response = self.client.post(self.transfer_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 200)

        recipient_wallet.refresh_from_db()
        self.assertEqual(recipient_wallet.balance, 100)

        self.assertEqual(Transaction.objects.count(), 2)

    def test_transfer_insufficient_balance(self):
        """
        Ensure a user cannot transfer more than their balance.
        """
        recipient_user = User.objects.create_user(username='recipient', email='recipient@example.com', password='password')
        recipient_wallet = Wallet.objects.get(user=recipient_user)
        data = {
            'recipient_wallet_id': str(recipient_wallet.wallet_id),
            'amount': '100.00'
        }
        response = self.client.post(self.transfer_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_to_self(self):
        """
        Ensure a user cannot transfer to their own wallet.
        """
        data = {
            'recipient_wallet_id': str(self.wallet.wallet_id),
            'amount': '10.00'
        }
        response = self.client.post(self.transfer_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_to_nonexistent_wallet(self):
        """
        Ensure a user cannot transfer to a non-existent wallet.
        """
        import uuid
        data = {
            'recipient_wallet_id': str(uuid.uuid4()),
            'amount': '10.00'
        }
        response = self.client.post(self.transfer_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class CommissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.golink_user = User.objects.create_superuser(
            username='golink_platform',
            email='platform@golink.com',
            password='password'
        )
        cls.golink_wallet = Wallet.objects.get(user=cls.golink_user)

    def test_commission_handling(self):
        """
        Test that commission is correctly handled.
        """
        provider_user = User.objects.create_user(username='provider', email='provider@example.com', password='password')
        provider_wallet = Wallet.objects.get(user=provider_user)
        provider_wallet.balance = 500
        provider_wallet.save()

        total_amount = Decimal('200.00')
        commission_rate = Decimal('0.10') # 10%

        handle_commission(provider_wallet, total_amount, commission_rate)

        provider_wallet.refresh_from_db()
        self.assertEqual(provider_wallet.balance, 480) # 500 - (200 * 0.10)

        self.golink_wallet.refresh_from_db()
        self.assertEqual(self.golink_wallet.balance, 20)

        self.assertEqual(Transaction.objects.filter(transaction_type='commission').count(), 2)


from rest_framework.test import APITransactionTestCase
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.util import random_hex
import pyotp
import base64
from django.db import connection


class WalletOTPTests(APITransactionTestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser_otp',
            email='otp@example.com',
            password='testpassword'
        )
        self.client.force_authenticate(user=self.user)
        self.wallet = Wallet.objects.get(user=self.user)
        self.wallet.balance = 500
        self.wallet.save()

        self.recipient = User.objects.create_user(
            username='recipient_otp',
            email='recipient_otp@example.com',
            password='testpassword'
        )
        self.recipient_wallet = Wallet.objects.get(user=self.recipient)

        self.transfer_url = reverse('wallets:transfer')
        self.verify_otp_url = reverse('wallets:verify_otp')

    def _create_confirmed_device(self):
        """
        Helper to create and commit a confirmed TOTPDevice for self.user.
        """
        device = TOTPDevice.objects.create(
            user=self.user,
            name="default",
            confirmed=True,
            key=random_hex()
        )
        connection.commit()
        return device

    def test_transfer_requires_otp(self):
        """
        Test that initiating a transfer requires OTP if 2FA is enabled.
        """
        self._create_confirmed_device()

        data = {
            'recipient_wallet_id': str(self.recipient_wallet.wallet_id),
            'amount': '100.00'
        }
        response = self.client.post(self.transfer_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('otp_required'))
        self.assertIn('otp_transaction_id', response.data)

    def test_transfer_no_2fa(self):
        """
        Test that a transfer fails if the user has no 2FA device.
        """
        data = {
            'recipient_wallet_id': str(self.recipient_wallet.wallet_id),
            'amount': '100.00'
        }
        response = self.client.post(self.transfer_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('2FA is not enabled', response.data['error'])

    def test_transfer_with_valid_otp(self):
        """
        Test completing a transfer with a valid OTP.
        """
        device = self._create_confirmed_device()

        # Step 1: Initiate transfer
        init_data = {
            'recipient_wallet_id': str(self.recipient_wallet.wallet_id),
            'amount': '100.00'
        }
        init_response = self.client.post(self.transfer_url, init_data, format='json')
        otp_transaction_id = init_response.data['otp_transaction_id']

        # Step 2: Verify OTP
        secret_b32 = base64.b32encode(bytes.fromhex(device.key)).decode()
        otp_code = pyotp.TOTP(secret_b32).now()

        verify_data = {
            'otp_transaction_id': otp_transaction_id,
            'otp_code': otp_code
        }
        verify_response = self.client.post(self.verify_otp_url, verify_data, format='json')

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_response.data['message'], 'Transfer successful')

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 400)
        self.recipient_wallet.refresh_from_db()
        self.assertEqual(self.recipient_wallet.balance, 100)

    def test_transfer_with_invalid_otp(self):
        """
        Test that completing a transfer with an invalid OTP fails.
        """
        self._create_confirmed_device()

        # Step 1: Initiate transfer
        init_data = {
            'recipient_wallet_id': str(self.recipient_wallet.wallet_id),
            'amount': '100.00'
        }
        init_response = self.client.post(self.transfer_url, init_data, format='json')
        otp_transaction_id = init_response.data['otp_transaction_id']

        # Step 2: Verify with invalid OTP
        verify_data = {
            'otp_transaction_id': otp_transaction_id,
            'otp_code': '123456'
        }
        verify_response = self.client.post(self.verify_otp_url, verify_data, format='json')

        self.assertEqual(verify_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid OTP code', verify_response.data['error'])

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 500) # Balance should not have changed
